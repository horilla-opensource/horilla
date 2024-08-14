"""
federal_tax.py

"""

CODE = '''
"""
federal_tax.py
"""

YEARLY_TAXABLE_INCOME = 189000.52


def calcluate_federal_tax(yearly_income: int, **kwargs) -> float:
    """
    Federal Tax calculation method

    yearly_income: The early converted 'based on' amount

    eg: yearly_income-> 189000 then taxable_amount-> 39312.0 (yearly)
    """

    def filter_brackets(brackets: list) -> list:
        """
        This method to filter out the actual brackets/brackets range
        """
        # brackets that contains actual bracket range, calculated_rate, and diff amount
        filterd_brackets = []
        for bracket in brackets:
            if bracket["max"] > bracket["min"]:

                # bracket: {'rate': 12, 'min': 11000, 'max': 44725}

                # finding diff amount and adding to the bracket
                bracket["diff"] = bracket["max"] - bracket["min"]
                # find bracket rate from the difference and adding to bracket
                bracket["calculated_rate"] = (bracket["rate"] / 100) * bracket["diff"]

                # bracket: {'rate': 12, 'min': 11000, 'max': 44725, 'diff': 33725, 'calculated_rate': 4047.0}

                filterd_brackets.append(bracket)
                continue
            # returning valid filtered brackets
            return filterd_brackets
        # returning valid filtered brackets
        return filterd_brackets

    # filter_brackets method/function will sort out the brackets

    # for example for the 189000 yearly income come in the 32% group,
    # so the final the max considered as min(231250,189000) which is 189000
    brackets = [
        {"rate": 10, "min": 0, "max": min(11000, yearly_income)},
        {"rate": 12, "min": 11000, "max": min(44725, yearly_income)},
        {"rate": 22, "min": 44725, "max": min(95375, yearly_income)},
        {"rate": 24, "min": 95375, "max": min(182100, yearly_income)},
        {"rate": 32, "min": 182100, "max": min(231250, yearly_income)},
        {"rate": 35, "min": 231250, "max": min(578125, yearly_income)},
        {"rate": 37, "min": 578125, "max": max(578125, yearly_income)},
    ]

    # filtering the brackets to actual range
    brackets = filter_brackets(brackets=brackets)

    # finding yearly taxable amount
    taxable_amount = sum(bracket["calculated_rate"] for bracket in brackets)

    """
    use formated_result method to print the table
    """
    # formated_result(brackets=brackets, taxable_amount=taxable_amount)

    # returning the taxable amount later on the yearly taxable amount-
    # is converted to daily and calculate federal tax for the total days between the
    # Payslip period
    return taxable_amount


def formated_result(brackets: dict, taxable_amount: float) -> None:
    """
    It will print the brackets such a formated way
    """
    col_width = 7
    print("----------------------Brackets----------------------")
    print(
        f"|{'Rate':<{col_width}}  |{'Min':<{col_width}} |{'Max':<{col_width}}  |{'Taxable':<{col_width}}  |{'Bracket Tax':<{col_width}} |"
    )

    for bracket in brackets:
        print(
            f"|{bracket['rate']:<{col_width}}% |{bracket['min']:<{col_width}} | {bracket['max']:<{col_width}} | {bracket['diff']:<{col_width}} | {round(bracket['calculated_rate'],2):<{col_width + 3}} |"
        )

    print(f"|             YEARLY TAXABLE INCOME    | {taxable_amount}    |")
    print("----------------------------------------------------")


month_taxable = calcluate_federal_tax(YEARLY_TAXABLE_INCOME)
print("YEARLY TAXABLE AMOUNT", month_taxable)

'''
