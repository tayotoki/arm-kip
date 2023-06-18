from django.contrib import admin
from datetime import date
import calendar


class InputFilter(admin.SimpleListFilter):
    template = 'admin/input_filter.html'

    def lookups(self, request, model_admin):
        # Тут нужно просто оставить пустой тапл, чтобы фильтр был на странице.
        return (
             ("", ""),
        )
    

class DateFilter(InputFilter):
    # Тут указываем название нашего поля, по которому будем фильтровать
    parameter_name = 'next_check_date'
    # Тут указываем заголовок фильтра
    title = 'Введите месяц даты замены'

    # Переназначаем queryset, если значение есть - фильтруем по нему
    def queryset(self, request, queryset):
        value = self.value()
        if value is not None:
            try:
                user_month = int(value.strip())
            except TypeError:
                return

            if user_month not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
                return
            
            end_day = calendar.monthrange(date.today().year, user_month)[1]
            start_day = 1
            last_date = date(date.today().year, user_month, end_day)
            start_date = last_date.replace(day=start_day)

            first_param, second_param = (
                self.parameter_name + "__gte",
                self.parameter_name + "__lte",
            )
            # **{key: value} - эта конструкция возьмет название поля из класса, сопоставит ему значение и распакует в метод фильтра.
            # Это тоже самое, что мы повторно напишем название поля вот так:
            # return queryset.filter(resource=value)
            return queryset.filter(**{first_param: start_date, second_param: last_date})
        
        return queryset
