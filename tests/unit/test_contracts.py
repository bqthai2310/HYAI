from hyai.compatibility import ContractRegistry


def test_frozen_contract_matrix_has_71_entries_and_full_closure():
    registry = ContractRegistry()
    assert len(registry.entries) == 71
    assert registry.validate_registry_closure()[0]


def test_contract_matrix_has_one_owner_writer_and_lifecycle_family_per_object():
    registry = ContractRegistry()
    assert len({entry["object_name"] for entry in registry.entries}) == len(registry.entries)
    assert all(entry["owner"] and entry["writer_commands"] and entry["lifecycle_family"] for entry in registry.entries)
