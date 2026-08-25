from django.db import migrations


def backfill_asset_items(apps, schema_editor):
    # Uses the historical models (not asset.models.Asset) and inlines the
    # same item-creation rule as Asset.sync_asset_items() at the time this
    # migration was written. Kept self-contained on purpose - a migration
    # must stay frozen even if sync_asset_items() changes or is removed
    # later, since a fresh install replays this file against whatever the
    # model looks like at migrate time, not when this was authored.
    Asset = apps.get_model("asset", "Asset")
    AssetItem = apps.get_model("asset", "AssetItem")
    AssetAssignment = apps.get_model("asset", "AssetAssignment")

    for asset in Asset.objects.all():
        existing = AssetItem.objects.filter(asset_id=asset).count()
        if existing < asset.quantity:
            base_id = asset.asset_tracking_id or f"AST{asset.pk}"
            AssetItem.objects.bulk_create(
                [
                    AssetItem(
                        asset_id=asset,
                        tracking_id=base_id if idx == 1 else f"{base_id}-{idx}",
                    )
                    for idx in range(existing + 1, asset.quantity + 1)
                ]
            )

        # Pre-existing, still-open assignments predate AssetItem and were
        # never linked to one - claim as many Available items as there are
        # open assignments so a currently-held asset doesn't get backfilled
        # as "Available".
        open_assignments = list(
            AssetAssignment.objects.filter(
                asset_id=asset, return_date__isnull=True, asset_item_id__isnull=True
            )
        )
        if not open_assignments:
            continue

        claimable_items = list(
            AssetItem.objects.filter(asset_id=asset, status="Available")[
                : len(open_assignments)
            ]
        )
        for assignment, item in zip(open_assignments, claimable_items):
            item.status = "In use"
            item.save()
            assignment.asset_item_id = item
            assignment.save()


class Migration(migrations.Migration):

    dependencies = [
        ("asset", "0005_assetitem_assetassignment_asset_item_id"),
    ]

    operations = [
        migrations.RunPython(backfill_asset_items, migrations.RunPython.noop),
    ]
