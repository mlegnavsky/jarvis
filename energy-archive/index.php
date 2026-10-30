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
    header('X-Jarvis-Auth-Input: ' . (($authorization !== '' || $user !== '') ? 'available' : 'missing'));
    header('WWW-Authenticate: Basic realm="Jarvis private backups", charset="UTF-8"');
    stop(401, 'Authentication required.');
}
// Telemetry stays outside document root; no URL-controlled paths or deletion API.
$dir=$home.'/jarvis-energy-archive';
if(is_link($dir)||(!is_dir($dir)&&!mkdir($dir,0700)))stop(503,'Archive directory unavailable');
if(!extension_loaded('pdo_sqlite'))stop(503,'SQLite unavailable');
$dbpath=$dir.'/archive.sqlite';if(is_link($dbpath))stop(503);
try {
$db=new PDO('sqlite:'.$dbpath);chmod($dbpath,0600);
$db->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);
$db->exec('PRAGMA busy_timeout=10000');
$db->exec('CREATE TABLE IF NOT EXISTS batches(hash TEXT PRIMARY KEY, data BLOB NOT NULL, received REAL NOT NULL)');
$db->exec('CREATE TABLE IF NOT EXISTS samples(t REAL PRIMARY KEY, data TEXT NOT NULL)');
$db->exec('CREATE TABLE IF NOT EXISTS publications(kind TEXT, issued REAL, data TEXT NOT NULL, PRIMARY KEY(kind,issued))');
$method=$_SERVER['REQUEST_METHOD'];
header('Content-Type: application/json');
if($method==='POST'){
 if((int)($_SERVER['CONTENT_LENGTH']??0)>1048576)stop(413);
 $raw=file_get_contents('php://input',false,null,0,1048577);if(strlen($raw)>1048576)stop(413);
 $hash=hash('sha256',$raw);$expected=$_SERVER['HTTP_X_BATCH_SHA256']??'';
 if(!hash_equals($hash,$expected))stop(400,'Batch hash mismatch');
 $rows=json_decode($raw,true,64,JSON_THROW_ON_ERROR);
 if(!is_array($rows)||!array_is_list($rows)||count($rows)>12||!count($rows))stop(400);
 foreach($rows as $r){
  if(!is_array($r)||!is_numeric($r['t']??null)||$r['t']<1577836800||$r['t']>time()+300||!in_array($r['kind']??'', ['sample','weather','spot'],true))stop(400,'Invalid record');
 }
 $db->beginTransaction();
 $q=$db->prepare('INSERT OR IGNORE INTO batches VALUES(?,?,?)');$q->execute([$hash,gzencode($raw,6),microtime(true)]);
 if($q->rowCount())foreach($rows as $r){
  $data=json_encode($r,JSON_THROW_ON_ERROR|JSON_UNESCAPED_UNICODE);
  if($r['kind']==='sample'){$q=$db->prepare('INSERT OR IGNORE INTO samples VALUES(?,?)');$q->execute([$r['t'],$data]);}
  else{$q=$db->prepare('INSERT OR IGNORE INTO publications VALUES(?,?,?)');$issued=strtotime($r['issued_at']??'');if($issued===false)throw new RuntimeException('Invalid issuance');$q->execute([$r['kind'],$issued,$data]);}
 }
 $db->commit();echo json_encode(['ack'=>$hash,'records'=>count($rows)]);exit;
}
if($method!=='GET')stop(405);
if(($_GET['op']??'status')==='status'){
 $q=$db->query('SELECT count(*),min(t),max(t),coalesce(sum(length(data)),0) FROM samples')->fetch(PDO::FETCH_NUM);
 $b=$db->query('SELECT count(*),coalesce(sum(length(data)),0) FROM batches')->fetch(PDO::FETCH_NUM);
 echo json_encode(['samples'=>(int)$q[0],'first'=>$q[1],'last'=>$q[2],'sample_bytes'=>(int)$q[3],'batches'=>(int)$b[0],'compressed_bytes'=>(int)$b[1],'database_bytes'=>filesize($dbpath),'free_bytes'=>disk_free_space($dir),'retention'=>'permanent']);exit;
}
if(($_GET['op']??'')!=='day')stop(400);
$start=filter_var($_GET['start']??null,FILTER_VALIDATE_FLOAT);$end=filter_var($_GET['end']??null,FILTER_VALIDATE_FLOAT);
if($start===false||$end===false||$start===null||$end===null||$end<=$start||$end-$start>90000)stop(400);
$q=$db->prepare('SELECT data FROM samples WHERE t>=? AND t<? ORDER BY t LIMIT 10000');$q->execute([$start,$end]);
$rows=[];while($r=$q->fetchColumn())$rows[]=json_decode($r,true);
$pub=[];foreach(['weather','spot'] as $kind){$cutoff=$kind==='weather'&&$end<time()?$start:min($end,time());$q=$db->prepare('SELECT data FROM publications WHERE kind=? AND issued<=? ORDER BY issued DESC LIMIT 1');$q->execute([$kind,$cutoff]);$r=$q->fetchColumn();if(!$r){$q=$db->prepare('SELECT data FROM publications WHERE kind=? AND issued<? ORDER BY issued ASC LIMIT 1');$q->execute([$kind,min($end,time())]);$r=$q->fetchColumn();}if($r)$pub[$kind]=json_decode($r,true);}
echo json_encode(['samples'=>$rows,'publications'=>$pub]);
} catch(Throwable $e){if(isset($db)&&$db->inTransaction())$db->rollBack();stop(503,'Private archive storage error');}
