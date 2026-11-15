<?php
/** Authenticated archive accounting. Raw samples are never rewritten. */
declare(strict_types=1);
function cash_number(mixed $v): ?float {
    return is_numeric($v) && is_finite((float)$v) ? (float)$v : null;
}
function cash_day(string $day): array {
    $start=new DateTimeImmutable($day.' 00:00:00',new DateTimeZone('Europe/Prague'));
    return [(float)$start->getTimestamp(),(float)$start->modify('+1 day')->getTimestamp()];
}
function cash_calculate(iterable $samples, array $prices, string $day): array {
    [$start,$end]=cash_day($day);$last=null;$meter=null;$bought=null;$reset=false;$sale=0.;$priced=0.;$quarters=[];$seen=0;$exportAt=null;$importAt=null;
    foreach($samples as $raw){
        $sample=is_string($raw)?json_decode($raw,true,64,JSON_THROW_ON_ERROR):$raw;
        $t=cash_number($sample['t']??null);if($t===null||$t<$start+120||$t>=$end)continue;
        $values=$sample['values']??[];$seen++;
        foreach(['export','import'] as $kind){
            $item=$values['sensor.inverter_today_energy_'.$kind]??[];
            $value=cash_number($item['value']??null);$stamp=strtotime($item['source_updated']??'');
            $changed=strtotime($item['source_changed']??'');
            if($value===null||$value<0||$stamp===false||$t-$stamp<0||$t-$stamp>120||($value>0&&($changed===false||$changed<$start)))continue;
            if($kind==='import'){if($bought!==null&&$value<$bought)$reset=true;$bought=$value;$importAt=$stamp;continue;}
            $exportAt=$stamp;
            $meter=max($meter??0.,$value);if($last!==null&&$value<$last['value'])$reset=true;
            if($last!==null&&$value>=$last['value']){
                $delta=$value-$last['value'];
                if($delta>0&&$stamp>$last['t']){
                    // A counter increment crossing a quarter can be priced only
                    // when every touched quarter has the same known price.
                    $rates=[];for($q=(int)floor($last['t']/900)*900;$q<$stamp;$q+=900){
                        if(!array_key_exists($q,$prices)){$rates=[];break;}$rates[]=$prices[$q];
                    }
                    if($rates&&(max($rates)-min($rates)<.0000001||$stamp-$last['t']<=30)){
                        $gross=$rates[0];
                        if(count($rates)>1&&$stamp>$last['t']){
                            $gross=0.;for($q=(int)floor($last['t']/900)*900;$q<$stamp;$q+=900){$seconds=max(0.,min($stamp,$q+900)-max($last['t'],$q));$gross+=$prices[$q]*$seconds/($stamp-$last['t']);}
                        }
                        $net=$gross-.30;$money=$delta*$net;$sale+=$money;$priced+=$delta;
                        $q=(int)floor(($stamp-.000001)/900)*900;$out=$quarters[$q]??['start'=>$q,'export_kwh'=>0.,'sale_czk'=>0.];
                        $out['export_kwh']+=$delta;$out['sale_czk']+=$money;$quarters[$q]=$out;
                    }
                }
            }
            $last=['t'=>$stamp,'value'=>$value];
        }
    }
    $missing=$meter===null?null:max(0.,$meter-$priced);$covered=!$reset&&$meter!==null&&$exportAt!==null&&$exportAt>=$end-180&&abs($meter-$priced)<.000001;
    $purchaseCovered=!$reset&&$bought!==null&&$importAt!==null&&$importAt>=$end-180;
    return ['date'=>$day,'export_kwh'=>$meter,'import_kwh'=>$bought,'priced_export_kwh'=>$priced,
        'unpriced_export_kwh'=>$missing,'known_sale_czk'=>$priced>0||$meter===0.?$sale:null,'sale_czk'=>$covered?$sale:null,
        'known_purchase_czk'=>$bought===null?null:$bought*5,'purchase_czk'=>$purchaseCovered?$bought*5:null,
        'cash_balance_czk'=>$covered&&$purchaseCovered?$sale-$bought*5:null,
        'last_export_measurement'=>$exportAt,'last_import_measurement'=>$importAt,'counter_reset'=>$reset,'quality'=>$covered&&$purchaseCovered?'estimate':'partial','samples'=>$seen,'quarters'=>array_values($quarters),
        'source'=>'private_archive_timed_daily_meter_increments','sale_fee'=>.30,'purchase_rate'=>5,
        'notice'=>'Odhad z časovaných přírůstků denního čítače; neoceněná energie není nulový výnos. Sazby5 Kč/kWh a poplatek0,30 Kč/kWh.' ];
}
function cash_prices(PDO $db,float $start,float $end): array {
    $q=$db->prepare("SELECT data FROM publications WHERE kind='spot' AND issued>=? AND issued<? ORDER BY issued DESC");
    $q->execute([$start-86400,$end]);$prices=[];
    while($raw=$q->fetchColumn()){
        $p=json_decode($raw,true,64,JSON_THROW_ON_ERROR)['attributes']??[];$rate=cash_number($p['rate']??null);
        foreach($p['rows']??[] as $row){$t=strtotime($row['time']??'');if($t===false||$t<$start||$t>=$end||isset($prices[$t]))continue;
            $eur=cash_number($row['eur_mwh']??null);$price=$rate!==null&&$eur!==null?$eur*$rate/1000:cash_number($row['price']??null);
            if($price!==null)$prices[$t]=$price;
        }
        if(count($prices)>=(int)(($end-$start)/900))break;
    }
    return $prices;
}
function cash_status(PDO $db,?float $first,int $budget=4): array {
    $db->exec('CREATE TABLE IF NOT EXISTS cash_days_v4(day TEXT PRIMARY KEY, count INTEGER, last REAL, price_last REAL, body TEXT NOT NULL)');
    $now=new DateTimeImmutable('now',new DateTimeZone('Europe/Prague'));$days=[];$pending=0;$built=0;
    // Latest completed day first; older history is warmed within a bounded budget.
    for($i=1;$i<=400;$i++){
        $day=$now->modify('-'.$i.' days')->format('Y-m-d');[$start,$end]=cash_day($day);if($first===null||$end<=$first)break;
        $q=$db->prepare('SELECT count(*),max(t) FROM samples WHERE t>=? AND t<?');$q->execute([$start,$end]);[$count,$last]=$q->fetch(PDO::FETCH_NUM);if(!$count)continue;
        $q=$db->prepare("SELECT max(issued) FROM publications WHERE kind='spot' AND issued>=? AND issued<?");$q->execute([$start-86400,$end]);$priceLast=$q->fetchColumn();
        $q=$db->prepare('SELECT count,last,price_last,body FROM cash_days_v4 WHERE day=?');$q->execute([$day]);$old=$q->fetch(PDO::FETCH_ASSOC);
        $dirty=!$old||(int)$old['count']!==(int)$count||(float)$old['last']!==(float)$last||(float)$old['price_last']!==(float)$priceLast;
        if($dirty&&$built<$budget){
            $prices=cash_prices($db,$start,$end);$q=$db->prepare('SELECT data FROM samples WHERE t>=? AND t<? ORDER BY t');$q->execute([$start,$end]);
            $rows=(function()use($q){while(($row=$q->fetchColumn())!==false)yield $row;})();
            $out=cash_calculate($rows,$prices,$day);$out['built_at']=time();
            $body=json_encode($out,JSON_THROW_ON_ERROR|JSON_UNESCAPED_UNICODE);
            $q=$db->prepare('INSERT OR REPLACE INTO cash_days_v4 VALUES(?,?,?,?,?)');$q->execute([$day,$count,$last,$priceLast,$body]);$built++;$dirty=false;
            $old=['body'=>$body];
        }
        if($dirty){$pending++;continue;}
        if($old){$out=json_decode($old['body'],true,64,JSON_THROW_ON_ERROR);unset($out['quarters']);$days[]=$out;}
    }
    return ['schema'=>2,'days'=>$days,'pending_days'=>$pending,'built_days'=>$built,'captured_at'=>time(),
        'source'=>'authenticated_private_archive','read_only_devices'=>true];
}
