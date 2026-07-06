from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
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
