from django.urls import path
from . import views
app_name="cultivation"
urlpatterns=[
 path("",views.cycle_list,name="list"),
 path("add/",views.cycle_form,name="add"),
 path("<int:pk>/edit/",views.cycle_form,name="edit"),
 path("select/",views.select_cycle,name="select"),
 path("dashboard/",views.cycle_dashboard,name="dashboard"),
 path("report/",views.cycle_report,name="report"),
 path("report/excel/",views.cycle_report_excel,name="report_excel"),
 path("report/pdf/",views.cycle_report_pdf,name="report_pdf"),
]
