from django.contrib import admin

from .models import AnimalTitle, CronJob

admin.site.register(AnimalTitle)


class CronJobAdmin(admin.ModelAdmin):
    list_display = ("name", "schedule", "last_execution", "next_execution")
    readonly_fields = (
        "name",
        "command",
        "schedule",
        "last_execution",
        "next_execution",
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["cronjobs"] = CronJob.objects.all()
        return super().changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        return False


admin.site.register(CronJob, CronJobAdmin)
