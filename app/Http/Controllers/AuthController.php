<?php
namespace App\Http\Controllers;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
class AuthController extends Controller {
    public function form() { return view('auth.login'); }
    public function login(Request $r) {
        $v=$r->validate(['email'=>'required|email','password'=>'required|string']);
        if (!Auth::attempt([...$v,'active'=>true],false)) return back()->withErrors(['email'=>'Email atau kata sandi tidak sesuai.'])->onlyInput('email');
        $r->session()->regenerate();
        return redirect()->intended(route('desk'));
    }
    public function logout(Request $r) {
        Auth::logout(); $r->session()->invalidate(); $r->session()->regenerateToken(); return redirect('/');
    }
    public function password(Request $r) {
        $v=$r->validate(['current_password'=>'required|current_password','password'=>'required|string|min:12|confirmed']);
        $r->user()->update(['password'=>$v['password']]); $r->session()->regenerate();
        return back()->with('success','Kata sandi diperbarui.');
    }
}
