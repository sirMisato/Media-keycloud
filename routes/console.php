<?php
use Illuminate\Support\Facades\{Artisan,Schedule};
use App\Models\User;
Artisan::command('media:publish-due',function () {
    $this->info(app(\App\Services\Editorial::class)->publishDue().' artikel diterbitkan.');
})->purpose('Publish approved scheduled revisions only');
Schedule::command('media:publish-due')->everyMinute()->withoutOverlapping();
Artisan::command('media:admin {email} {--name=Administrator}',function () {
    $email=$this->argument('email');
    if (!filter_var($email,FILTER_VALIDATE_EMAIL)) { $this->error('Email tidak valid.'); return 1; }
    if (User::where('email',$email)->exists()) { $this->error('Email sudah terdaftar.'); return 1; }
    $password=$this->secret('Kata sandi baru (minimal 12 karakter)');
    if (strlen($password ?? '')<12 || $password!==$this->secret('Ulangi kata sandi')) { $this->error('Kata sandi tidak sesuai.'); return 1; }
    $u=new User(['name'=>$this->option('name'),'email'=>$email,'password'=>$password]); $u->role='admin'; $u->save();
    $this->info('Admin dibuat. Silakan masuk melalui /masuk.');
})->purpose('Create the initial administrator without default credentials');
Artisan::command('media:reset-password {email}',function () {
    $u=User::where('email',$this->argument('email'))->first();
    if (!$u) { $this->error('Akun tidak ditemukan.'); return 1; }
    $p=$this->secret('Kata sandi baru (minimal 12 karakter)');
    if (strlen($p ?? '')<12 || $p!==$this->secret('Ulangi kata sandi')) { $this->error('Kata sandi tidak sesuai.'); return 1; }
    $u->password=$p; $u->save(); $this->info('Kata sandi diperbarui.');
})->purpose('Recover an account from the VPS console');
