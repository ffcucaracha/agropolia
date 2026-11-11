from agropolia.ids import uuid7


def test_uuid7_shape():
    value = uuid7()
    assert value.version == 7
    assert value.variant == 'specified in RFC 4122'
