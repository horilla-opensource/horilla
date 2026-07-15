from django.core.exceptions import PermissionDenied

from hydra_links.selectors import public_link_location_ids_for_user


def save_public_hydra_link(*, link, actor):
    permission = (
        "hydra_links.add_publichydralink"
        if link._state.adding
        else "hydra_links.change_publichydralink"
    )
    if not actor.has_perm(permission):
        raise PermissionDenied
    if link.location_id:
        if link.location_id not in set(
            public_link_location_ids_for_user(user=actor)
        ):
            raise PermissionDenied
    elif not actor.has_perm("hydra_links.manage_global_publichydralink"):
        raise PermissionDenied
    link.full_clean()
    if link._state.adding:
        link.created_by = actor
    link.modified_by = actor
    link.save()
    return link
