from django.db.models import Count

from django_pewtils.managers import BasicExtendedManager
from django_pewtils import get_model


class LoggedExtendedManager(BasicExtendedManager):
    def create_or_update(
        self,
        unique_data,
        update_data=None,
        match_any=False,
        return_object=True,
        search_nulls=False,
        save_nulls=False,
        empty_lists_are_null=True,
        only_update_existing_nulls=False,
        logger=None,
        command_log=None,
        force_create=False,
        **save_kwargs
    ):
        existing = super(LoggedExtendedManager, self).create_or_update(
            unique_data,
            update_data=update_data,
            match_any=match_any,
            return_object=return_object,
            search_nulls=search_nulls,
            save_nulls=save_nulls,
            empty_lists_are_null=empty_lists_are_null,
            only_update_existing_nulls=only_update_existing_nulls,
            logger=logger,
            force_create=force_create,
            **save_kwargs
        )
        if existing and command_log:
            existing.command_logs.add(command_log)
            existing.commands.add(command_log.command)
        return existing
