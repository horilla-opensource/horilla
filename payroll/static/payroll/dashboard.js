$(document).ready(function(){ 

    var myDate = new Date();
    var year = myDate.getFullYear();
    var month = ('0' + (myDate.getMonth())).slice(-2); // Month is zero-indexed, so add 1 and pad with leading zero if needed
    var formattedDate = year + '-' + month;
    var start_index=0;
    var per_page=10 

    $("#monthYearField").val(formattedDate); 
    
    
    function employee_chart(dataSet, labels) {
        $("#employee_canvas_body").html('<canvas id="employeeChart"></canvas>');
    
        const employeeChart = document.getElementById('employeeChart').getContext("2d");
        
        $.ajax({
            url: '/payroll/get-language-code',
            type: "GET",
            success: (response) => {
                const scaleXText = response.scale_x_text;
                const scaleYText = response.scale_y_text;
    
                const employeeChartData = {
                    labels: labels,
                    datasets: dataSet
                };
    
                window["employeeChart"] = {};
    
                // Chart constructor
                var employeePayrollChart = new Chart(employeeChart, {
                    type: "bar",
                    data: employeeChartData,
                    options: {
                        scales: {
                            x: {
                                stacked: true,
                                title: {
                                    display: true,
                                    text: scaleXText,
                                    font: {
                                        weight: "bold",
                                        size: 16,
                                    },
                                },
                            },
                            y: {
                                stacked: true,
                                title: {
                                    display: true,
                                    text: scaleYText,
                                    font: {
                                        weight: "bold",
                                        size: 16,
                                    },
                                },
                            }
                        }
                    }
                });
    
                $("#employeeChart").on("click", function (event) {
                    var activeBars = employeePayrollChart.getElementsAtEventForMode(event, "index", { intersect: true }, true);
    
                    if (activeBars.length > 0) {
                        var clickedBarIndex = activeBars[0].index;
                        var clickedLabel = employeeChartData.labels[clickedBarIndex];
    
                        $.ajax({
                            url: '/payroll/filter-payslip?dashboard=true&search=' + clickedLabel,
                            type: "GET",
                            dataType: "html",
                            headers: {
                                "X-Requested-With": "XMLHttpRequest",
                            },
                            success: (response) => {
                                $("#back_button").removeClass("d-none")
                                $("#dashboard").html(response)
                            },
                            error: (error) => {
                                console.log('Error', error);
                            }
                        });
                    }
                });
            },
            error: (error) => {
                console.log('Error', error);
            }
        });
    }    

    var  employee_chart_view = (dataSet,labels) =>{

        var period = $("#monthYearField").val()
        
        $.ajax({
            url: '/payroll/dashboard-employee-chart',
            type: "GET",
            dataType: "json",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
            data:{
                "period":period,
            },
            success: (response) => {
                dataSet = response.dataset;
                labels = response.labels;
                employees = response.employees

                $("#select_employee").html("")
                $("#select_employee").append("<option></option>")
                
                $.each(employees,function(key,item) {

                    $("#select_employee").append($('<option>', {
                        value: item[0],
                        text: item[1]+" " + item[2]
                    }));
                });

                $.each(dataSet,function(key,item) {
                    item["data"]=item.data.slice(start_index,start_index+per_page,)
                });
                var values = Object.values(labels).slice(start_index, start_index + per_page);

                employee_chart(dataSet,values)
            },
            error: (error) => {
                console.log('Error', error);
            }
        });
    }

    function payslip_details(){
        var period = $("#monthYearField").val()
        $.ajax({
            url: '/payroll/dashboard-payslip-details',
            type: "GET",
            dataType: "json",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
            data:{
                "period":period,
            },
            success: (response) => {

                $(".payslip-number").html(response.no_of_emp)
                $(".payslip-amount").html(response.total_amount)

            },
            error: (error) => {
                console.log('Error', error);
            }
        });
    } 

    function department_chart_view (){
        var period = $("#monthYearField").val()
        function department_chart(dataSet,labels){
            $("#department_canvas_body").html('<canvas id="departmentChart"></canvas>')
            

            const departmentChartData = {
                labels: labels,
                datasets: dataSet
                
            };

            window["departmentChart"] = {};
            const departmentChart = document.getElementById('departmentChart');
            
            // chart constructor
            var departmentPayrollChart = new Chart(departmentChart, {
                type: "pie",
                data: departmentChartData,
            });

            $("#departmentChart").on("click", function(event) {
                var activeBars = departmentPayrollChart.getElementsAtEventForMode(event, "index", { intersect: true }, true);
        
                if (activeBars.length > 0) {
                    var clickedBarIndex = activeBars[0].index;
                    var clickedLabel = departmentChartData.labels[clickedBarIndex];
                    
                    $.ajax({
                        url: '/payroll/filter-payslip?dashboard=true&department='+clickedLabel,
                        type: "GET",
                        dataType: "html",
                        headers: {
                            "X-Requested-With": "XMLHttpRequest",
                        },
                        success: (response) => {
                            $("#back_button").removeClass("d-none")
                            $("#dashboard").html(response)
            
            
                        },
                        error: (error) => {
                            console.log('Error', error);
                        }
                    });
                }
            });
        }

        $.ajax({
            url: '/payroll/dashboard-department-chart',
            type: "GET",
            dataType: "json",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
            data:{
                "period":period,
            },
            success: (response) => {
                dataSet = response.dataset;
                labels = response.labels;
                department_total = response.department_total

                $("#department_total").html("")
                $.each(department_total, function (key, value) {
                    $("#department_total").append(
                        "<li class='m-3 department'><span class='department_item'>"+value["department"]+"</span>: <span>"+value["amount"]+"</span></li>"
                        )
                    })


                department_chart(dataSet,labels)
            },
            error: (error) => {
                console.log('Error', error);
            }
        });
    }
    
    function contract_ending(){
        var period = $("#monthYearField").val()
        $.ajax({
            url: '/payroll/dashboard-contract-ending',
            type: "GET",
            dataType: "json",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
            data:{
                "period":period,
            },
            success: (response) => {
                var contract_end = response.contract_end
                

                $("#contract_ending").html("")
                $.each(contract_end, function (key,value) {
                    id=value.contract_id
                    elem = `<li class='m-3 contract_id' data-id=${id}> ${value.contract_name} </li>`
                    
                    $("#contract_ending").append(elem)
                    })
                $(".contract-number").html(Object.keys(contract_end).length)

            },
            error: (error) => {
                console.log('Error', error);
            }
        });

    }


    employee_chart_view ()
    payslip_details()
    department_chart_view()
    contract_ending()

      
    $("#monthYearField").on("change",function(){
        employee_chart_view()
        payslip_details()
        department_chart_view()
        contract_ending()
    })

    $("#payroll-employee-next").on("click" ,function () {
        var period = $("#monthYearField").val()
        $.ajax({
            url: '/payroll/dashboard-employee-chart',
            type: "GET",
            dataType: "json",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
            data:{
                "period":period,
            },
            success: (response) => {
                dataSet = response.dataset;
                labels = response.labels;

                updated_data= dataSet
                if (start_index == 0){
                    start_index+=per_page
                }
                $.each(updated_data,function(key,item) {
                    item["data"]=item.data.slice(start_index,start_index+per_page)
                });
                
                var values = Object.values(labels).slice(start_index, start_index + per_page);
                if (values.length>0){
                employee_chart(updated_data,values)
                start_index+=per_page
            }
            },
            error: (error) => {
                console.log('Error', error);
            }
        });
        
    })

    $("#employee-previous").on("click" ,function () {
        var period = $("#monthYearField").val()
        $.ajax({
            url: '/payroll/dashboard-employee-chart',
            type: "GET",
            dataType: "json",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
            data:{
                "period":period,
            },
            success: (response) => {
                dataSet = response.dataset;
            labels = response.labels;
            
            if (start_index <= 0) {
                return;
            }
            start_index -= per_page;
            if (start_index > 0) {
                updated_data = dataSet.map(item => ({
                    ...item,
                    data: item.data.slice(start_index - per_page, start_index)
                }));
                var values = Object.values(labels).slice(start_index - per_page, start_index);
                employee_chart(updated_data, values);
            }
            },
            error: (error) => {
                console.log('Error', error);
            }
        });
        
    })

    $("#export").on("click",function(){

        var period = $("#monthYearField").val()
        var start_date = $("#start_date").val()
        var end_date = $("#end_date").val()
        var employee = $("#select_employee").val()
        var status = $("#select_status").val()

        let url = "/payroll/dashboard-export/"+"?start_date="+start_date+"&end_date="+end_date+"&employee="+employee+"&status="+status;
        window.location.href = url;

    })

    $(".filter").on("click", function(){
        $("#back_button").removeClass("d-none")
    })

    $("#contract_ending").on("click", ".contract_id", function() {
        id = $(this).data("id")
        $.ajax({
            url: '/payroll/single-contract-view/'+id,
            type: "GET",
            dataType: "html",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
            data:{
                "dashboard":"dashboard"
            },
            success: (response) => {
                $("#ContractModal").toggleClass("oh-modal--show")
                $("#contract_target").html(response)


            },
            error: (error) => {
                console.log('Error', error);
            }
        });

    });

    $("#ContractModal").on("click",".oh-modal__close",function(){
        $("#ContractModal").removeClass("oh-modal--show")
    })

    $("#department_total").on("click",".department",function(){
        department = $(this).children(".department_item").text()
        $.ajax({
            url: '/payroll/filter-payslip?department='+department,
            type: "GET",
            dataType: "html",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
            success: (response) => {
                $("#back_button").removeClass("d-none")
                $("#dashboard").html(response)


            },
            error: (error) => {
                console.log('Error', error);
            }
        });
    })
    


    

})