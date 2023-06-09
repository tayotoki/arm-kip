from openpyxl import Workbook
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from datetime import datetime, date
from .export_excel import ExportExcelAction
from openpyxl.styles import Font
from unidecode import unidecode
from .models import KipReport
from django.contrib import messages
from django.db.models import Q


def style_output_file(file):
    black_font = Font(color='000000', bold=True)
    for cell in file["1:1"]:
        cell.font = black_font

    for column_cells in file.columns:
        length = max(len((cell.value)) for cell in column_cells)
        length += 10
        file.column_dimensions[column_cells[0].column_letter].width = length

    return file


def convert_data_date(value):
    return value.strftime('%d/%m/%Y')


def convert_boolean_field(value):
    if value:
        return 'Yes'
    return 'No'


def export_as_xls(self, request, queryset):
    if not request.user.is_staff:
        raise PermissionDenied
    opts = self.model._meta
    field_names = self.list_display
    file_name = unidecode(opts.verbose_name)
    blank_line = []
    wb = Workbook()

    ws = wb.active
    ws.append(ExportExcelAction.generate_header(self, self.model, field_names))

    for obj in queryset:
        row = []
        for field in field_names:
            is_admin_field = hasattr(self, field)
            if is_admin_field:
                value = getattr(self, field)(obj)
            else:
                value = getattr(obj, field)
                if isinstance(value, datetime) or isinstance(value, date):
                    value = convert_data_date(value)
                elif isinstance(value, bool):
                    value = convert_boolean_field(value)
            row.append(str(value) if value is not None else "--")
        ws.append(row)

    ws = style_output_file(ws)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename={file_name}.xlsx'
    wb.save(response)
    return response


def add_to_kipreport(self, request, queryset):
    if request.user.groups.filter(~Q(name="КИП")):
        self.message_user(
            request,
            "У вас нет доступа к данной функции",
            messages.ERROR,
        )
        return

    editable_kip_report = KipReport.objects.filter(
        editable=True,
    ).last()

    queryset = queryset.exclude(
        pk__in=[
            device.pk for device in queryset if device.status in (
                device.send,
                device.in_progress,
            ) or (device.stock is None or device.station)
        ]
    )

    if not queryset:
        self.message_user(
            request,
            f"Ни один прибор не был добавлен в отчет. "
            f"Возможные причины:\n "
            f"- Приборы не на складе,\n - Приборы уже были добавлены "
            f"в текущий или другой отчеты КИП",
            messages.ERROR,
        )

        return

    if editable_kip_report:
        editable_kip_report.devices.set(queryset | editable_kip_report.devices.all())

        self.message_user(
            request,
            f"Выделенные приборы были добавлены в отчет {editable_kip_report}",
            messages.SUCCESS,
        )

    else:
        new_kip_report = KipReport.objects.create(author=request.user)

        new_kip_report.devices.set(queryset)

        self.message_user(
            request,
            f"Отчет КИП №{new_kip_report.pk} был успешно создан и в него добавлены выделенные приборы",
            messages.SUCCESS,
        )



export_as_xls.short_description = "Экспортировать в Excel"
add_to_kipreport.short_description = "Добавить в отчет КИП"