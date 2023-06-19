from django.contrib import admin
from datetime import date
import calendar


class InputFilter(admin.SimpleListFilter):
    # template = 'admin/input_filter.html'

    def lookups(self, request, model_admin):
        return (
            ("1", "январь"),
            ("2", "февраль"),
            ("3", "март"),
            ("4", "апрель"),
            ("5", "май"),
            ("6", "июнь"),
            ("7", "июль"),
            ("8", "август"),
            ("9", "сентябрь"),
            ("10", "октябрь"),
            ("11", "ноябрь"),
            ("12", "декабрь"),
        )

    def has_output(self):
        return True

    # def choices(self, changelist):
    #     return list(range(0, 13))
    

class DateFilter(InputFilter):
    parameter_name = 'next_check_date'
    title = 'Фильтр по выбранному месяцу'

    def queryset(self, request, queryset):
        value = self.value()

        if value is not None:
            try:
                user_month = int(value.strip())
            except ValueError:
                return

            if user_month not in range(1, 13):
                return
            
            end_day = calendar.monthrange(date.today().year, user_month)[1]
            start_day = 1
            last_date = date(date.today().year, user_month, end_day)
            start_date = last_date.replace(day=start_day)

            first_param, second_param = (
                self.parameter_name + "__gte",
                self.parameter_name + "__lte",
            )

            return queryset.filter(**{first_param: start_date,
                                      second_param: last_date})
        
        return queryset
