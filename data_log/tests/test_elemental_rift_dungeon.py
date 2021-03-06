from datetime import timedelta

from data_log import models
from .test_log_views import BaseLogTest


class ElementalRiftBeastTests(BaseLogTest):
    fixtures = ['test_game_items', 'test_levels']

    def test_elementa_rift_parse(self):
        response = self._do_log('BattleRiftDungeonResult/fire_beast_b.json')
        self.assertEqual(response.status_code, 200)

        log = models.RiftDungeonLog.objects.first()
        self.assertEqual(log.grade, models.RiftDungeonLog.GRADE_B)
        self.assertEqual(log.total_damage, 728860)
        self.assertEqual(log.clear_time, timedelta(milliseconds=191284))
        self.assertFalse(log.success)

    def test_elemental_rift_level_parsed_correctly(self):
        self._do_log('BattleRiftDungeonResult/fire_beast_b.json')
        log = models.RiftDungeonLog.objects.last()
        self.assertEqual(log.level, models.Level.objects.get(
            dungeon__category=models.Dungeon.CATEGORY_RIFT_OF_WORLDS_BEASTS,
            dungeon__com2us_id=2001,
            floor=1,
        ))

        self._do_log('BattleRiftDungeonResult/water_beast_a.json')
        log = models.RiftDungeonLog.objects.last()
        self.assertEqual(log.level, models.Level.objects.get(
            dungeon__category=models.Dungeon.CATEGORY_RIFT_OF_WORLDS_BEASTS,
            dungeon__com2us_id=1001,
            floor=1,
        ))

    def test_elemental_rift_failed(self):
        self._do_log('BattleRiftDungeonResult/water_beast_fail.json')
        log = models.RiftDungeonLog.objects.first()
        self.assertEqual(log.grade, models.RiftDungeonLog.GRADE_F)
        self.assertFalse(log.success)

    def test_elemental_rift_rune_drop(self):
        self._do_log('BattleRiftDungeonResult/fire_beast_b.json')
        log = models.RiftDungeonLog.objects.first()
        self.assertEqual(log.runes.count(), 1)

    def test_elemental_rift_craft_item_drop(self):
        self._do_log('BattleRiftDungeonResult/water_beast_a.json')
        log = models.RiftDungeonLog.objects.first()
        self.assertEqual(log.items.count(), 2)

    def test_elemental_rift_shapeshifting_stone_drop(self):
        self._do_log('BattleRiftDungeonResult/fire_beast_sss_transmog_stone.json')
        log = models.RiftDungeonLog.objects.first()
        self.assertEqual(log.items.filter(item__category=models.GameItem.CATEGORY_CURRENCY, item__com2us_id=6).count(), 1)

    def test_quit_before_any_damage(self):
        self._do_log('BattleRiftDungeonResult/fire_beast_quit_no_damage.json')
        log = models.RiftDungeonLog.objects.first()
        self.assertEqual(log.total_damage, 0)
        self.assertEqual(log.grade, models.RiftDungeonLog.GRADE_F)
