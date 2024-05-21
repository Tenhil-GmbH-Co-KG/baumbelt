from enum import EnumMeta


class EnumContainsMeta(EnumMeta):
    """
    Constructing Enums with this metaclass will allow for `in` checks.
    Note, that this only checks for the existence in the Enum members,
    not the respective values. Similar to dictionary lookups: `"key" in dict_instance`

    ```
        class AtomEnum(Enum, metaclass=EnumContainsMeta):
            hydrogen = 1
            helium = 2
            lithium = 3
            neon = 10

        "hydrogen" in AtomEnum  # True
        "sulfur" in AtomEnum    # False
        "water" not in AtomEnum  # True
    ```
    """

    def __contains__(cls, item):
        return item in cls.__members__
