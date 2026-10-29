<?php
/** Jarvis private backup WebDAV v1.0.0. Flat, append-only storage for native HA. */
declare(strict_types=1);
ini_set('display_errors', '0');
umask(0077);
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
header('X-Robots-Tag: noindex, nofollow');
function stop(int $status, string $message = ''): never {
    http_response_code($status);
    header('Content-Type: text/plain; charset=utf-8');
    echo $message;
    exit;
}
// Fixed private sibling of httpdocs; no remotely configurable filesystem path.
$home = dirname(__DIR__, 2);
$private = $home . '/ha-backups';
$configPath = $private . '/access.json';
if (is_link($private) || !is_dir($private) || is_link($configPath) || !is_file($configPath)) {
    stop(503, 'Private backup storage is not configured.');
}
$config = json_decode((string) @file_get_contents($configPath), true);
if (!is_array($config) || ($config['username'] ?? '') !== 'jarvis-backup' ||
    !is_string($config['password_hash'] ?? null) || strlen($config['password_hash']) < 40) {
    stop(503, 'Private backup credentials are not configured.');
}
$authorization = $_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '';
$user = $_SERVER['PHP_AUTH_USER'] ?? '';
$password = $_SERVER['PHP_AUTH_PW'] ?? '';
if (preg_match('/^Basic\s+(.+)$/i', $authorization, $match)) {
    $decoded = base64_decode($match[1], true);
    if ($decoded !== false && str_contains($decoded, ':')) {
        [$user, $password] = explode(':', $decoded, 2);
    }
}
if (!hash_equals($config['username'], $user) || !password_verify($password, $config['password_hash'])) {
    header('WWW-Authenticate: Basic realm="Jarvis private backups", charset="UTF-8"');
    stop(401, 'Authentication required.');
}
$root = $private . '/objects';
if (is_link($root) || (!is_dir($root) && !@mkdir($root, 0700)) || !is_writable($root)) {
    stop(503, 'Private backup storage is unavailable.');
}
$base = $_SERVER['SCRIPT_NAME'];
$rawPath = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
if (!is_string($rawPath) || !str_starts_with($rawPath, $base)) stop(400);
$name = rawurldecode(substr($rawPath, strlen($base)));
$name = ltrim($name, '/');
function valid_name(string $name): bool {
    return strlen($name) <= 220 && preg_match('/\A[A-Za-z0-9][A-Za-z0-9_.-]*\.(?:tar|metadata\.json)\z/D', $name) === 1;
}
if ($name !== '' && !valid_name($name)) stop(403, 'Only flat backup archive and metadata names are allowed.');
$path = $name === '' ? $root : $root . '/' . $name;
if (is_link($path)) stop(403);
$method = $_SERVER['REQUEST_METHOD'];
if (!in_array($method, ['OPTIONS', 'PROPFIND', 'GET', 'HEAD', 'PUT'], true)) {
    header('Allow: OPTIONS, PROPFIND, GET, HEAD, PUT');
    stop(405, 'Deletion and collection mutations are disabled.');
}
if ($method === 'OPTIONS') {
    header('DAV: 1');
    header('Allow: OPTIONS, PROPFIND, GET, HEAD, PUT');
    stop(200);
}
function xml(string $s): string { return htmlspecialchars($s, ENT_XML1 | ENT_QUOTES, 'UTF-8'); }
if ($method === 'PROPFIND') {
    $depth = $_SERVER['HTTP_DEPTH'] ?? '1';
    if (!in_array($depth, ['0', '1'], true)) stop(403, 'Only depth 0 or 1 is supported.');
    if (!file_exists($path)) stop(404);
    $items = [$name];
    if ($name === '' && $depth === '1') {
        foreach (scandir($root) as $file) {
            if (valid_name($file) && !is_link($root . '/' . $file) && is_file($root . '/' . $file)) $items[] = $file;
        }
    }
    http_response_code(207);
    header('Content-Type: application/xml; charset=utf-8');
    echo '<?xml version="1.0" encoding="utf-8"?><d:multistatus xmlns:d="DAV:">';
    foreach ($items as $item) {
        $isRoot = $item === '';
        $file = $isRoot ? $root : $root . '/' . $item;
        $href = $base . '/' . ($isRoot ? '' : rawurlencode($item));
        echo '<d:response><d:href>' . xml($href) . '</d:href><d:propstat><d:prop>';
        echo '<d:displayname>' . xml($isRoot ? 'Jarvis Backups' : $item) . '</d:displayname>';
        echo '<d:resourcetype>' . ($isRoot ? '<d:collection/>' : '') . '</d:resourcetype>';
        echo '<d:getcontentlength>' . ($isRoot ? 0 : filesize($file)) . '</d:getcontentlength>';
        echo '<d:getlastmodified>' . gmdate('D, d M Y H:i:s', (int) filemtime($file)) . ' GMT</d:getlastmodified>';
        echo '<d:getcontenttype>' . ($isRoot ? 'httpd/unix-directory' : 'application/octet-stream') . '</d:getcontenttype>';
        echo '</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>';
    }
    echo '</d:multistatus>';
    exit;
}
if ($name === '') stop(405);
if ($method === 'GET' || $method === 'HEAD') {
    if (!is_file($path)) stop(404);
    header('Content-Type: application/octet-stream');
    header('Content-Length: ' . filesize($path));
    if ($method === 'GET') readfile($path);
    exit;
}
$length = $_SERVER['CONTENT_LENGTH'] ?? '';
if (!preg_match('/\A[0-9]+\z/D', (string) $length)) stop(411);
$length = (int) $length;
$limit = str_ends_with($name, '.metadata.json') ? 1048576 : 4294967296;
if ($length < 1 || $length > $limit) stop(413);
// Serialize uploads from this endpoint so concurrent PUTs cannot each spend the reserve.
$lockPath = $private . '/uploads.lock';
if (is_link($lockPath)) stop(503);
$uploadLock = @fopen($lockPath, 'c');
if ($uploadLock === false) stop(503);
if (!flock($uploadLock, LOCK_EX | LOCK_NB)) {
    fclose($uploadLock);
    header('Retry-After: 30');
    stop(423, 'Another backup upload is in progress.');
}
register_shutdown_function(static function () use ($uploadLock): void {
    flock($uploadLock, LOCK_UN);
    fclose($uploadLock);
});
$free = disk_free_space($root);
if ($free === false || $free - $length < 1073741824) stop(507, 'Free space reserve reached.');
@set_time_limit(3600);
$tmp = tempnam($root, '.incoming-');
if ($tmp === false) stop(507);
register_shutdown_function(static function () use ($tmp): void { if (is_file($tmp)) @unlink($tmp); });
$in = fopen('php://input', 'rb');
$out = fopen($tmp, 'wb');
if ($in === false || $out === false) stop(500);
$written = stream_copy_to_stream($in, $out, $length + 1);
$flushed = fflush($out);
if (function_exists('fsync')) $flushed = fsync($out) && $flushed;
fclose($out); fclose($in);
if ($written !== $length || !$flushed) stop(400, 'Incomplete upload.');
// Atomic, no-overwrite publish. Identical retries succeed; conflicts preserve the old file.
if (!@link($tmp, $path)) {
    clearstatcache(true, $path);
    if (is_link($path) || !is_file($path)) stop(409);
    if (filesize($path) !== $length || !hash_equals(hash_file('sha256', $tmp), hash_file('sha256', $path))) stop(412, 'Existing backup cannot be overwritten.');
    stop(204);
}
stop(201);
