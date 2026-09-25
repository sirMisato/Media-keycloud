<?php
namespace App\Http\Controllers;
use App\Models\{User,Setting,AuditLog};
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
class AdminController extends Controller {
    private function admin(Request $r): void { abort_unless($r->user()->isAdmin(),403); }
    public function users(Request $r) { $this->admin($r); return view('desk.users',['users'=>User::orderBy('name')->paginate(30)]); }
    public function createUser(Request $r) {
        $this->admin($r);
        $v=$r->validate(['name'=>'required|string|max:120','email'=>'required|email|max:200|unique:users',
            'password'=>'required|string|min:12|confirmed','role'=>'required|in:contributor,admin']);
        $u=new User($v); $u->role=$v['role']; $u->save();
        AuditLog::create(['user_id'=>$r->user()->id,'action'=>'user_created','note'=>'User #'.$u->id]);
        return back()->with('success','Akun dibuat. Sampaikan kredensial kepada pemilik melalui kanal privat.');
    }
    public function toggle(Request $r,User $user) {
        $this->admin($r); abort_if($r->user()->id===$user->id,422,'Tidak dapat menonaktifkan akun sendiri.');
        DB::transaction(function () use ($r,$user) {
            $u=User::whereKey($user->id)->lockForUpdate()->firstOrFail();
            $u->active=!$u->active; $u->save();
            AuditLog::create(['user_id'=>$r->user()->id,'action'=>'user_active_changed','note'=>'User #'.$u->id.' active='.(int)$u->active]);
        });
        return back()->with('success','Status akun diperbarui.');
    }
    public function settings(Request $r) { $this->admin($r); return view('desk.settings',['settings'=>Setting::values()]); }
    public function saveSettings(Request $r) {
        $this->admin($r);
        $v=$r->validate(['name'=>'required|string|max:60','tagline'=>'required|string|max:120','location'=>'required|string|max:80',
            'about'=>'required|string|max:3000','editorial'=>'required|string|max:3000','email'=>'nullable|email|max:200',
            'logo'=>'nullable|file|image|mimes:png,jpg,jpeg,webp|max:2048|dimensions:max_width=2000,max_height=2000']);
        unset($v['logo']);
        if ($r->hasFile('logo')) $v['logo']=$r->file('logo')->store('covers','local');
        foreach ($v as $key=>$value) Setting::updateOrCreate(['key'=>$key],['value'=>$value ?? '']);
        return back()->with('success','Identitas media diperbarui.');
    }
}
