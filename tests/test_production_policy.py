import copy
import unittest

from production_policy import choose_operation, complete_battery_plan, house_profile_issues
from owner_settings import DEFAULTS


class ProductionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.now=1793977200.0
        self.block={'day':'2026-11-06','start':self.now-900,'end':self.now+3600}
        self.price={'start':self.now,'end':self.now+900,'net':7}
        self.settings={'pv_verified':True,'bias_verified':True,'bias_enabled':True}
        self.states={}
        for i in range(1,7):
            self.states.update({f'number.inverter_program_{i}_soc':'30',
                f'number.inverter_program_{i}_power':'12000',f'select.inverter_program_{i}_charging':'Disabled'})
    def choose(self,**changes):
        args=dict(block=self.block,price=self.price,soc=80,pv_w=0,house_w=300,
                  now=self.now,policy=DEFAULTS,settings=self.settings,states=self.states)
        args.update(changes)
        return choose_operation(**args)
    def test_scheduled_battery_wins_and_inputs_are_unchanged(self):
        before=copy.deepcopy((self.block,self.settings,self.states))
        self.assertEqual(self.choose(soc=99,pv_w=4000)['mode'],'battery')
        self.assertEqual(before,(self.block,self.settings,self.states))
    def test_before_start_and_after_end_never_start_large_battery_sale(self):
        for block in ({**self.block,'start':self.now+1},{**self.block,'end':self.now}):
            self.assertEqual(self.choose(block=block)['mode'],'bias')
    def test_surplus_requires_real_headroom_and_known_house_power(self):
        for pv,house,expected in ((4000,300,'pv'),(0,300,'bias'),(200,300,'bias'),(4000,None,'bias')):
            self.assertEqual(self.choose(block=None,soc=97,pv_w=pv,house_w=house)['mode'],expected)
    def test_sixty_is_not_the_bias_cutoff(self):
        self.assertEqual(self.choose(soc=60)['mode'],'bias')
        self.assertEqual(self.choose(soc=31)['mode'],'bias')
        self.assertEqual(self.choose(soc=30)['mode'],'hold')
    def test_bias_remains_eligible_at_negative_price_but_not_missing_price(self):
        self.assertEqual(self.choose(price={**self.price,'net':-1})['mode'],'bias')
        self.assertEqual(self.choose(price=None)['mode'],'hold')
    def test_completed_day_cannot_restart_large_sale_after_soc_rebound(self):
        self.settings['completed_battery_plan']={**self.block,'reason':'reserve'}
        self.assertEqual(self.choose(soc=65)['mode'],'bias')
        tomorrow={**self.block,'day':'2026-11-07'}
        self.assertEqual(self.choose(block=tomorrow,soc=65)['mode'],'battery')
    def test_external_native_profile_mismatch_is_read_only_and_blocks_export(self):
        self.states['number.inverter_program_3_soc']='45'
        before=copy.deepcopy(self.states)
        self.assertEqual(self.choose()['mode'],'hold')
        issues=house_profile_issues(self.states)
        self.assertEqual(issues[0]['entity_id'],'number.inverter_program_3_soc')
        self.assertEqual(issues[0]['expected'],30)
        self.assertEqual(before,self.states)
    def test_ha_home_floor_does_not_change_native_profile_requirement(self):
        self.assertFalse(house_profile_issues(self.states))
        self.assertEqual(self.choose(soc=45,policy={**DEFAULTS,'home_soc':45,'resume_soc':46})['mode'],'hold')
    def test_invalid_soc_and_stale_price_never_authorize_export(self):
        for soc in (None,float('nan'),-1,101):self.assertEqual(self.choose(soc=soc)['mode'],'hold')
        self.assertEqual(self.choose(price={**self.price,'end':self.now})['mode'],'hold')
        self.assertEqual(self.choose(soc=55,settings={**self.settings,'bias_verified':False})['mode'],'bias')
    def proof(self,**changes):
        return {'id':'cycle','purpose':'automatic','start':self.block['start'],
                'end':self.block['end'],'reason':'reserve','stop_verified':True,'conflicts':{},**changes}
    def test_reserve_completion_survives_settings_copy_and_does_not_change_other_data(self):
        settings={**self.settings,'selected_block':self.block,'rate_history':[{'at':1,'purchase_rate':5}]}
        new=complete_battery_plan(settings,self.proof(),self.now)
        self.assertEqual(new['completed_battery_plan']['day'],'2026-11-06')
        self.assertEqual(new['rate_history'],settings['rate_history'])
        self.assertNotIn('completed_battery_plan',settings)
    def test_partial_segment_deadline_is_not_whole_business_plan_completion(self):
        settings={'selected_block':self.block}
        new=complete_battery_plan(settings,self.proof(reason='deadline',end=self.now+300),self.now+300)
        self.assertNotIn('completed_battery_plan',new)
        end=self.block['end']
        self.assertIn('completed_battery_plan',complete_battery_plan(settings,self.proof(reason='deadline'),end))
    def test_fault_manual_and_unconfirmed_stops_never_mark_plan_complete(self):
        for change in ({'reason':'health'},{'reason':'manual'},{'stop_verified':False},
                       {'conflicts':{'143':{}}},{'purpose':'commission'},{'start':self.now-999999}):
            self.assertNotIn('completed_battery_plan',complete_battery_plan({'selected_block':self.block},self.proof(**change),self.now))

    def test_live_completed_blocks_identity_survives_upgrade(self):
        import json
        key=json.dumps([self.block['day'],float(self.block['start']),float(self.block['end'])],separators=(',',':'))
        self.settings['completed_blocks']={key:{'sale_id':'old','reason':'reserve'}}
        self.assertEqual(self.choose(soc=70)['mode'],'bias')

    def test_legacy_completed_day_blocks_truncated_or_reselected_same_day_plan(self):
        import json
        key=json.dumps([self.block['day'],float(self.block['start']),float(self.block['end'])],separators=(',',':'))
        self.settings['completed_blocks']={key:{'sale_id':'old','reason':'reserve'}}
        for block in ({**self.block,'end':self.block['end']-300},{**self.block,'start':self.block['start']-300}):
            self.assertEqual(self.choose(block=block,soc=70)['mode'],'bias')
        self.assertEqual(self.choose(block={**self.block,'day':'2026-11-07'},soc=70)['mode'],'battery')
