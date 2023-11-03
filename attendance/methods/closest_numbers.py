"""
closest_numbers.py
"""


def closest_numbers(numbers: list, input_number: int) -> tuple:
    """
    This method is used to find previous and next of numbers
    """
    previous_number = input_number
    next_number = input_number
    try:
        index = numbers.index(input_number)
        if index > 0:
            previous_number = numbers[index - 1]
        else:
            previous_number = numbers[-1]
        if index + 1 == len(numbers):
            next_number = numbers[0]
        elif index < len(numbers):
            next_number = numbers[index + 1]
        else:
            next_number = numbers[0]
    except:
        pass
    return (previous_number, next_number)
