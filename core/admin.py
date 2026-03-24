from django.contrib import admin

from .models import Distillation, Memory


@admin.register(Memory)
class MemoryAdmin(admin.ModelAdmin):
    list_display = ("id", "short_content", "created_datetime", "updated_datetime")
    search_fields = ("content",)
    readonly_fields = ("sv", "embedding", "created_datetime", "updated_datetime")
    ordering = ("-created_datetime",)

    @admin.display(description="Content")
    def short_content(self, obj: Memory) -> str:
        return obj.content[:80] + "..." if len(obj.content) > 80 else obj.content


@admin.register(Distillation)
class DistillationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "short_content",
        "memory_id",
        "created_datetime",
        "updated_datetime",
    )
    search_fields = ("content",)
    readonly_fields = ("sv", "embedding", "created_datetime", "updated_datetime")
    list_select_related = ("memory",)
    ordering = ("-created_datetime",)
    raw_id_fields = ("memory",)

    @admin.display(description="Content")
    def short_content(self, obj: Distillation) -> str:
        return obj.content[:80] + "..." if len(obj.content) > 80 else obj.content
