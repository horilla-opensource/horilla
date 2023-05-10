from django_filters import FilterSet
from django_filters import FilterSet, CharFilter
import django_filters
from .models import Asset,AssetAssignment,AssetCategory,AssetRequest,AssetLot
from django import forms
import uuid

    

class CustomFilterSet(FilterSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.filters.items():
            filter_widget = self.filters[field_name]
            widget = filter_widget.field.widget
            if isinstance(widget, (forms.NumberInput, forms.EmailInput,forms.TextInput)):
                filter_widget.field.widget.attrs.update({'class': 'oh-input w-100'})
            elif isinstance(widget,(forms.Select,)):
                filter_widget.field.widget.attrs.update({'class': 'oh-select oh-select-2',})
            elif isinstance(widget,(forms.Textarea)):
                filter_widget.field.widget.attrs.update({'class': 'oh-input w-100'})
            elif isinstance(widget, (forms.CheckboxInput,forms.CheckboxSelectMultiple,)):
                filter_widget.field.widget.attrs.update({'class': 'oh-switch__checkbox'})
            elif isinstance(widget,(forms.ModelChoiceField)):
                filter_widget.field.widget.attrs.update({'class': 'oh-select oh-select-2 ',})
            elif isinstance(widget,(forms.DateField)):
                filter_widget.field.widget.attrs.update({'type': 'date','class':'oh-input  w-100'})
            if isinstance(field, django_filters.CharFilter):
                field.lookup_expr='icontains'
            
   
class AssetExportFilter(CustomFilterSet):
    
    class Meta:
        model = Asset
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(AssetExportFilter, self).__init__(*args, **kwargs)
        self.form.fields['asset_purchase_date'].widget.attrs.update({'type':'date'})
        
class AssetFilter(CustomFilterSet):
    class Meta:
        model = Asset
        fields = '__all__'
    def __init__(self,*args,**kwargs):
        super(AssetFilter,self).__init__(*args,**kwargs)
        for visible in self.form.visible_fields():
            visible.field.widget.attrs['id'] = str(uuid.uuid4())
    

class CustomAssetFilter(CustomFilterSet):
    asset_id__asset_name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = AssetAssignment
        fields =['asset_id__asset_name','asset_id__asset_status',]
    def __init__(self,*args,**kwargs):
        super(CustomAssetFilter,self).__init__(*args,**kwargs)
        for visible in self.form.visible_fields():
            visible.field.widget.attrs['id'] = str(uuid.uuid4())

      
class AssetRequestFilter(CustomFilterSet):
    class Meta:
        model = AssetRequest
        fields = '__all__'
    def __init__(self,*args,**kwargs):
        super(AssetRequestFilter,self).__init__(*args,**kwargs)
        for visible in self.form.visible_fields():
            visible.field.widget.attrs['id'] = str(uuid.uuid4())
      
class AssetAllocationFilter(CustomFilterSet):
    class Meta:
        model = AssetAssignment
        fields = '__all__'
    def __init__(self,*args,**kwargs):
        super(AssetAllocationFilter,self).__init__(*args,**kwargs)
        for visible in self.form.visible_fields():
            visible.field.widget.attrs['id'] = str(uuid.uuid4())
     
class AssetCategoryFilter(CustomFilterSet):
    class Meta:
        model = AssetCategory
        fields = '__all__'
    def __init__(self,*args,**kwargs):
        super(AssetCategoryFilter,self).__init__(*args,**kwargs)
        for visible in self.form.visible_fields():
            visible.field.widget.attrs['id'] = str(uuid.uuid4())
  
