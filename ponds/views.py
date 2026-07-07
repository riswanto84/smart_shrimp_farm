from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from accounts.rbac import permission_required
from .models import Pond
@login_required
@permission_required('ponds.view')
def list_ponds(request): return render(request,'ponds/list.html',{'ponds':Pond.objects.all()})
@login_required
@permission_required('ponds.view')
def add_pond(request):
    if request.method=='POST':
        Pond.objects.create(code=request.POST['code'], name=request.POST['name'], area_m2=request.POST.get('area_m2') or 0, depth_m=request.POST.get('depth_m') or 0, capacity_seed=request.POST.get('capacity_seed') or 0, status=request.POST.get('status','Persiapan'), location=request.POST.get('location',''), notes=request.POST.get('notes',''))
        return redirect('ponds:list')
    return render(request,'ponds/form.html')
@login_required
@permission_required('ponds.view')
def detail_pond(request, pk): return render(request,'ponds/detail.html',{'pond':get_object_or_404(Pond,pk=pk)})


@login_required
@permission_required('ponds.view')
def edit_pond(request, pk):
    pond = get_object_or_404(Pond, pk=pk)
    if request.method == 'POST':
        pond.code = request.POST['code']
        pond.name = request.POST['name']
        pond.area_m2 = request.POST.get('area_m2') or 0
        pond.depth_m = request.POST.get('depth_m') or 0
        pond.capacity_seed = request.POST.get('capacity_seed') or 0
        pond.pond_type = request.POST.get('pond_type','')
        pond.status = request.POST.get('status','Persiapan')
        pond.location = request.POST.get('location','')
        if request.FILES.get('photo'):
            pond.photo = request.FILES.get('photo')
        pond.notes = request.POST.get('notes','')
        pond.save()
        return redirect('ponds:list')
    return render(request, 'ponds/form.html', {'pond': pond, 'mode': 'edit'})

@login_required
@permission_required('ponds.view')
@require_POST
def delete_pond(request, pk):
    get_object_or_404(Pond, pk=pk).delete()
    return redirect('ponds:list')
