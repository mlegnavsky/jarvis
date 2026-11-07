<?php
// Generates credentials only. This page cannot write server configuration or backup files.
declare(strict_types=1);
header('Cache-Control: no-store, private');
header('X-Robots-Tag: noindex, nofollow');
header('Referrer-Policy: no-referrer');
header("Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'");
$password = bin2hex(random_bytes(24));
$config = json_encode(['username' => 'jarvis-backup', 'password_hash' => password_hash($password, PASSWORD_DEFAULT)], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
?><!doctype html><html lang="cs"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Soukromé zálohy Jarvise</title>
<style>body{font:18px system-ui;max-width:760px;margin:50px auto;padding:20px;line-height:1.6;background:#f5f7fb;color:#142037}code{overflow-wrap:anywhere;background:#e5eaf3;padding:5px}a{display:inline-block;padding:12px;background:#174fbb;color:white;border-radius:8px}</style>
<h1>Připojení soukromých záloh</h1>
<p>Tato stránka vytvořila nové náhodné heslo. Úložiště zatím neaktivovala.</p>
<ol><li>Ulož si toto heslo do správce hesel: <code><?=htmlspecialchars($password)?></code></li>
<li><a download="access.json" href="data:application/json;base64,<?=base64_encode($config)?>">Stáhnout access.json</a></li>
<li>V Plesku nahraj tento soubor do složky <strong>ha-backups vedle httpdocs</strong>. Nikdy do httpdocs. Nastav oprávnění souboru na 600 (čtení a zápis jen vlastník).</li>
<li>V Home Assistantu přidej integraci <strong>WebDAV</strong>: URL <code>https://laborator.odladeni.cz/backup-dav/index.php/</code>, uživatel <code>jarvis-backup</code>, heslo výše, cesta <code>/</code>, ověřování SSL zapnuté.</li></ol>
<p>Po připojení ještě vyber WebDAV v umístěních záloh a ověř skutečnou šifrovanou zálohu. Automatické mazání na tomto úložišti je vypnuté.</p>
<p>Obnovením této stránky vzniknou jiné údaje. Použij heslo a access.json ze stejného zobrazení. Heslo do chatu neposílej.</p></html>
