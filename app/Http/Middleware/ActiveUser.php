<?php
namespace App\Http\Middleware;
use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
class ActiveUser {
    public function handle(Request $request,Closure $next) {
        if (!$request->user()?->active) {
            Auth::logout(); $request->session()->invalidate(); $request->session()->regenerateToken();
            return redirect()->route('login')->withErrors(['email'=>'Akun tidak aktif. Hubungi redaksi.']);
        }
        return $next($request);
    }
}
