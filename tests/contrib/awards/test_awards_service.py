# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2022 CERN.
#
# Invenio-Vocabularies is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Test the award vocabulary service."""

from copy import deepcopy

import pytest
from invenio_pidstore.errors import PIDAlreadyExists
from invenio_records.systemfields.relations.errors import InvalidRelationValue
from marshmallow.exceptions import ValidationError

from invenio_vocabularies.contrib.awards.api import Award


def test_simple_flow(
    app, service, identity, award_full_data, example_funder
):
    """Test a simple vocabulary service flow."""
    # Create it
    item = service.create(identity, award_full_data)
    id_ = item.id

    # add dereferenced data
    expected_data = deepcopy(award_full_data)
    expected_data["funder"]["name"] = "CERN"

    assert id_ == award_full_data['pid']
    for k, v in expected_data.items():
        assert item.data[k] == v

    # Read it
    read_item = service.read(identity, '755021')
    assert item.id == read_item.id
    assert item.data == read_item.data

    # Refresh index to make changes live.
    Award.index.refresh()

    # Search it
    res = service.search(
        identity, q=f"id:{id_}", size=25, page=1)
    assert res.total == 1
    assert list(res.hits)[0] == read_item.data

    # Update it
    data = read_item.data
    data['title']['en'] = 'New title'
    update_item = service.update(identity, id_, data)
    # the pid is not save to the json metadata
    assert not update_item._record.get("pid")
    assert item.id == update_item.id
    assert update_item['title']['en'] == 'New title'

    # Delete it
    assert service.delete(identity, id_)

    # Refresh to make changes live
    Award.index.refresh()

    # Fail to retrieve it
    # - db
    # only the metadata is removed from the record, it is still resolvable
    base_keys = {"created", "updated", "id", "links", "revision_id", "pid"}
    deleted_rec = service.read(identity, id_).to_dict()
    assert set(deleted_rec.keys()) == base_keys
    # - search
    res = service.search(
        identity, q=f"id:{id_}", size=25, page=1)
    assert res.total == 0

    # not-ideal cleanup
    item._record.delete(force=True)


def test_create_invalid_funder(
    app, service, identity, award_full_data, example_funder
):
    award_with_invalid_funder = deepcopy(award_full_data)
    award_with_invalid_funder["funder"]["id"] = "invalid"
    pytest.raises(
        InvalidRelationValue,
        service.create,
        identity,
        award_with_invalid_funder
    )


def test_pid_already_registered(
    app, db, service, identity, award_full_data, example_award
):
    # example_funder does the first creation
    pytest.raises(
        PIDAlreadyExists, service.create, identity, award_full_data)


def test_extra_fields(
    app, service, identity, award_full_data, example_funder
):
    """Extra fields in data should fail."""
    award_full_data['invalid'] = 1
    pytest.raises(
        ValidationError, service.create, identity, award_full_data)


def test_award_dereferenced(
    app, service, identity, award_full_data, example_funder
):
    """Extra fields in data should fail."""
    expected_funder = {
        "id": "01ggx4157",
        "name": "CERN",
    }
    assert not award_full_data["funder"].get("name")
    # Create it
    item = service.create(identity, award_full_data)
    Award.index.refresh()
    id_ = item.id
    # assert item["funder"] == expected_funder

    # Read it
    read_item = service.read(identity, id_)
    assert read_item["funder"] == expected_funder

    # Search it
    res = service.search(
        identity, q=f"id:{id_}", size=25, page=1)
    assert res.total == 1
    assert list(res.hits)[0]["funder"] == expected_funder
