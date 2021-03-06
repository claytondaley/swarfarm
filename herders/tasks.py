from celery import shared_task, current_task, states
from datetime import datetime, timezone, timedelta
from django.db import transaction
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.core import mail

from .models import Summoner, Storage, MonsterInstance, MonsterPiece, RuneInstance, RuneCraftInstance, BuildingInstance
from .profile_parser import parse_sw_json
from .signals import update_profile_date


@shared_task
def com2us_data_import(data, user_id, import_options):
    summoner = Summoner.objects.get(pk=user_id)
    imported_monsters = []
    imported_runes = []
    imported_crafts = []
    imported_pieces = []

    # Import the new objects
    with transaction.atomic():
        if import_options['clear_profile']:
            RuneInstance.objects.filter(owner=summoner).delete()
            RuneCraftInstance.objects.filter(owner=summoner).delete()
            MonsterInstance.objects.filter(owner=summoner).delete()
            MonsterPiece.objects.filter(owner=summoner).delete()

    results = parse_sw_json(data, summoner, import_options)

    if not current_task.request.called_directly:
        current_task.update_state(state=states.STARTED, meta={'step': 'summoner'})

    # Disconnect summoner profile last update post-save signal to avoid mass spamming updates
    post_save.disconnect(update_profile_date, sender=MonsterInstance)
    post_save.disconnect(update_profile_date, sender=RuneInstance)
    post_save.disconnect(update_profile_date, sender=RuneCraftInstance)

    with transaction.atomic():
        # Update summoner and inventory
        if results['wizard_id']:
            summoner.com2us_id = results['wizard_id']
            summoner.save()

        summoner.storage.magic_essence[Storage.ESSENCE_LOW] = results['inventory'].get('storage_magic_low', 0)
        summoner.storage.magic_essence[Storage.ESSENCE_MID] = results['inventory'].get('storage_magic_mid', 0)
        summoner.storage.magic_essence[Storage.ESSENCE_HIGH] = results['inventory'].get('storage_magic_high', 0)
        summoner.storage.fire_essence[Storage.ESSENCE_LOW] = results['inventory'].get('storage_fire_low', 0)
        summoner.storage.fire_essence[Storage.ESSENCE_MID] = results['inventory'].get('storage_fire_mid', 0)
        summoner.storage.fire_essence[Storage.ESSENCE_HIGH] = results['inventory'].get('storage_fire_high', 0)
        summoner.storage.water_essence[Storage.ESSENCE_LOW] = results['inventory'].get('storage_water_low', 0)
        summoner.storage.water_essence[Storage.ESSENCE_MID] = results['inventory'].get('storage_water_mid', 0)
        summoner.storage.water_essence[Storage.ESSENCE_HIGH] = results['inventory'].get('storage_water_high', 0)
        summoner.storage.wind_essence[Storage.ESSENCE_LOW] = results['inventory'].get('storage_wind_low', 0)
        summoner.storage.wind_essence[Storage.ESSENCE_MID] = results['inventory'].get('storage_wind_mid', 0)
        summoner.storage.wind_essence[Storage.ESSENCE_HIGH] = results['inventory'].get('storage_wind_high', 0)
        summoner.storage.light_essence[Storage.ESSENCE_LOW] = results['inventory'].get('storage_light_low', 0)
        summoner.storage.light_essence[Storage.ESSENCE_MID] = results['inventory'].get('storage_light_mid', 0)
        summoner.storage.light_essence[Storage.ESSENCE_HIGH] = results['inventory'].get('storage_light_high', 0)
        summoner.storage.dark_essence[Storage.ESSENCE_LOW] = results['inventory'].get('storage_dark_low', 0)
        summoner.storage.dark_essence[Storage.ESSENCE_MID] = results['inventory'].get('storage_dark_mid', 0)
        summoner.storage.dark_essence[Storage.ESSENCE_HIGH] = results['inventory'].get('storage_dark_high', 0)

        summoner.storage.wood = results['inventory'].get('wood', 0)
        summoner.storage.leather = results['inventory'].get('leather', 0)
        summoner.storage.rock = results['inventory'].get('rock', 0)
        summoner.storage.ore = results['inventory'].get('ore', 0)
        summoner.storage.mithril = results['inventory'].get('mithril', 0)
        summoner.storage.cloth = results['inventory'].get('cloth', 0)
        summoner.storage.rune_piece = results['inventory'].get('rune_piece', 0)
        summoner.storage.dust = results['inventory'].get('powder', 0)
        summoner.storage.symbol_harmony = results['inventory'].get('symbol_harmony', 0)
        summoner.storage.symbol_transcendance = results['inventory'].get('symbol_transcendance', 0)
        summoner.storage.symbol_chaos = results['inventory'].get('symbol_chaos', 0)
        summoner.storage.crystal_water = results['inventory'].get('crystal_water', 0)
        summoner.storage.crystal_fire = results['inventory'].get('crystal_fire', 0)
        summoner.storage.crystal_wind = results['inventory'].get('crystal_wind', 0)
        summoner.storage.crystal_light = results['inventory'].get('crystal_light', 0)
        summoner.storage.crystal_dark = results['inventory'].get('crystal_dark', 0)
        summoner.storage.crystal_magic = results['inventory'].get('crystal_magic', 0)
        summoner.storage.crystal_pure = results['inventory'].get('crystal_pure', 0)
        summoner.storage.save()

        # Save imported buildings
        for bldg in results['buildings']:
            bldg.save()

        # Set missing buildings to level 0
        BuildingInstance.objects.filter(owner=summoner).exclude(pk__in=[bldg.pk for bldg in results['buildings']]).update(level=0)

    if not current_task.request.called_directly:
        current_task.update_state(state=states.STARTED, meta={'step': 'monsters'})

    with transaction.atomic():
        # Save the imported monsters
        for idx, mon in enumerate(results['monsters']):
            mon.save()
            imported_monsters.append(mon.pk)

        # Update saved monster pieces
        for piece in results['monster_pieces']:
            piece.save()
            imported_pieces.append(piece.pk)

    if not current_task.request.called_directly:
        current_task.update_state(state=states.STARTED, meta={'step': 'runes'})

    with transaction.atomic():
        # Save imported runes
        for idx, rune in enumerate(results['runes']):
            # Refresh the internal assigned_to_id field, as the monster didn't have a PK when the
            # relationship was previously set.
            rune.assigned_to = rune.assigned_to
            rune.save()
            imported_runes.append(rune.pk)

    if not current_task.request.called_directly:
        current_task.update_state(state=states.STARTED, meta={'step': 'crafts'})

    with transaction.atomic():
        # Save imported rune crafts
        for idx, craft in enumerate(results['crafts']):
            craft.save()
            imported_crafts.append(craft.pk)

    with transaction.atomic():
        # Delete objects missing from import
        if import_options['delete_missing_monsters']:
            MonsterInstance.objects.filter(owner=summoner).exclude(pk__in=imported_monsters).delete()
            MonsterPiece.objects.filter(owner=summoner).exclude(pk__in=imported_pieces).delete()

        if import_options['delete_missing_runes']:
            RuneInstance.objects.filter(owner=summoner).exclude(pk__in=imported_runes).delete()
            RuneCraftInstance.objects.filter(owner=summoner).exclude(pk__in=imported_crafts).delete()


@shared_task
def delete_inactive_users():
    # Remove any user inactive for 6+ months
    delete_threshold = datetime.now(timezone.utc) - timedelta(weeks=4 * 6)
    death_row = User.objects.filter(last_login__lte=delete_threshold)[:100]  # Limit quantity of users. Task is called frequently.

    emails = []
    subject = 'SWARFARM - Inactive Account Deleted'
    body = (
        "Hello {},\n\n"
        "Your SWARFARM account has been inactive for 6 months or more! "
        "Due to this, your account has been deleted along with all associated data.\n\n" 
        "-SWARFARM"
    )
    for user in death_row:
        # Unassociate all logs related to this user, if any
        user.summoner.summonlog_set.update(summoner=None)
        user.summoner.runlog_set.update(summoner=None)
        user.summoner.riftdungeonlog_set.update(summoner=None)
        user.summoner.runecraftlog_set.update(summoner=None)
        user.summoner.shoprefreshlog_set.update(summoner=None)
        user.summoner.worldbosslog_set.update(summoner=None)
        user.summoner.riftraidlog_set.update(summoner=None)
        user.summoner.wishlog_set.update(summoner=None)

        emails.append((
            subject,
            body.format(user.username),
            'noreply@swarfarm.com',
            [user.email]
        ))

        user.delete()

    # Notify of account deletion
    mail.send_mass_mail(emails)

