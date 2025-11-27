def extract_payslip_row(payslip, allowance_titles, deduction_titles):
    data = payslip.pay_head_data

    row = {
        "Employee": payslip.employee_id.get_full_name(),
        "Basic Pay": data.get("basic_pay", 0),
        "Loss of Pay": data.get("loss_of_pay", 0),
        "Total for EPF": data.get("basic_pay", 0) - data.get("loss_of_pay", 0),
    }


    allowance_map = {
        a.get("title"): a.get("amount", 0)
        for a in data.get("allowances", [])
    }


    lop_deduction_map = {}

    for d in data.get("pretax_deductions", []):
        title = d.get("title", "")
        amt = d.get("amount", 0)

        if title.endswith("(LOP deduction)"):
            alw_title = title.replace("(LOP deduction)", "").strip()
            lop_deduction_map[alw_title] = amt

    total_lop_deductions = 0
    total_net_allowances = 0


    for title in allowance_titles:
        original_amt = allowance_map.get(title, 0)
        lop_amt = lop_deduction_map.get(title, 0)

        net_amt = original_amt - lop_amt

        row[title] = net_amt
        row[f"{title} (LOP deduction)"] = lop_amt

        total_lop_deductions += lop_amt
        total_net_allowances += net_amt

    row["Total Allowance LOP Deductions"] = total_lop_deductions
    row["Total Net Allowances"] = total_net_allowances


    row["Gross Pay"] = data.get("gross_pay", 0)


    pretax_deductions_map = {
        d.get("title"): d.get("amount", 0)
        for d in data.get("pretax_deductions", [])
        if not d.get("title", "").endswith("(LOP deduction)")
    }

    deduction_titles = [
        d for d in deduction_titles
        if d not in [f"{alw} (LOP deduction)" for alw in allowance_titles]
    ]

    for title in deduction_titles:
        row[title] = pretax_deductions_map.get(title, 0)

    post_tax_deduction_map = {
        d.get("title"): d.get("amount", 0)
        for d in data.get("post_tax_deductions", [])
    }

    total_post_tax = 0

    for title, amount in post_tax_deduction_map.items():
        row[title] = amount
        total_post_tax += amount


    row["Total Post-Tax Deductions"] = total_post_tax
    row["Total Deductions"] = data.get("total_deductions", 0)
    row["Net Pay"] = data.get("net_pay", 0)
    row["EPF Employer 12%"] = data.get("employer_epf_amount", 0)
    row["ETF Employer 3%"] = data.get("employer_etf_amount", 0)
    row["Paid Days"] = data.get("paid_days", 0)
    row["Unpaid Days"] = data.get("unpaid_days", 0)
    row["No of Pays"] = 1

    row["Total for Tax"] = (data.get("gross_pay", 0) - data.get("loss_of_pay", 0)) - total_lop_deductions

    return row

