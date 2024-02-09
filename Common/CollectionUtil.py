
class CollectionUtil:

    @staticmethod
    def divide_chunks(items: list, size: int) -> list:
        items_to_split = list(items)
        result = []
        for i in range(0, len(items_to_split), size):
            result.append(items_to_split[i:i + size])

        return result
