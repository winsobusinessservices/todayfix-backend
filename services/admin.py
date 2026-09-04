from django.contrib import admin

from .models import SearchLog, SearchSynonym, Service
from .models import ServiceType, Unit, ServiceEmployee


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "service_uuid",
        "name",
        "business",
        "category",
        "price",
        "duration",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "category",
    )

    search_fields = (
        "service_uuid",
        "name",
        "business__name",
    )

    readonly_fields = (
        "service_uuid",
        "created_at",
        "updated_at",
    )

@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "slug",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "service_type",
        "is_active",
        "created_at",
    )

    list_filter = (
        "service_type",
        "is_active",
    )

    search_fields = (
        "name",
        "service_type__name",
    )


@admin.register(ServiceEmployee)
class ServiceEmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "service_employee_uuid",
        "service",
        "employee",
        "created_at",
    )

    search_fields = (
        "service_employee_uuid",
        "service__name",
        "employee__name",
    )


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    """
    Review this list filtered by result_count=0 to find real
    search phrases users tried that nothing matched — then
    decide whether the service catalog is missing something,
    or whether a new synonym needs to be added by hand.
    """

    list_display = (
        "search_term",
        "result_count",
        "user",
        "created_at",
    )

    list_filter = (
        "result_count",
    )

    search_fields = (
        "search_term",
    )

    readonly_fields = (
        "search_term",
        "result_count",
        "user",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SearchSynonym)
class SearchSynonymAdmin(admin.ModelAdmin):
    """
    Add manual synonym pairs here after reviewing zero-result
    Search Logs — e.g. term="putting", synonym="installation".
    Matching applies in both directions.
    """

    list_display = (
        "term",
        "synonym",
        "created_at",
    )

    search_fields = (
        "term",
        "synonym",
    )