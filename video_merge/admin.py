from django.contrib import admin

from video_merge.models import MergeClip, MergeJob


class MergeClipInline(admin.TabularInline):
    model = MergeClip
    extra = 0
    readonly_fields = ("order", "original_name", "created_at")


@admin.register(MergeJob)
class MergeJobAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "name", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "owner__username", "id")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [MergeClipInline]
