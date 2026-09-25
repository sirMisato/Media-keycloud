<?php
use Illuminate\Support\Facades\Route;
use App\Http\Controllers\{PublicController,AuthController,DeskController,AdminController};
Route::get('/',[PublicController::class,'home'])->name('home');
Route::get('/artikel',[PublicController::class,'index'])->name('articles');
Route::get('/kanal/{slug}',[PublicController::class,'index'])->name('channel');
Route::get('/baca/{slug}',[PublicController::class,'article'])->name('article');
Route::get('/halaman/{page}',[PublicController::class,'page'])->name('page');
Route::get('/media/{path}',[PublicController::class,'cover'])->name('cover');
Route::get('/robots.txt',[PublicController::class,'robots']);
Route::get('/sitemap.xml',[PublicController::class,'sitemap']);
Route::middleware('guest')->group(function () {
    Route::get('/masuk',[AuthController::class,'form'])->name('login');
    Route::post('/masuk',[AuthController::class,'login'])->middleware('throttle:6,1');
});
Route::middleware(['auth','active','auth.session'])->prefix('redaksi')->group(function () {
    Route::get('/',[DeskController::class,'index'])->name('desk');
    Route::post('/keluar',[AuthController::class,'logout'])->name('logout');
    Route::get('/akun',fn () => view('desk.account'))->name('account');
    Route::post('/kata-sandi',[AuthController::class,'password'])->middleware('throttle:6,1')->name('password.change');
    Route::get('/tulis',[DeskController::class,'create'])->name('write');
    Route::post('/naskah',[DeskController::class,'store'])->name('draft.store');
    Route::get('/revisi/{revision}',[DeskController::class,'edit'])->name('editor');
    Route::put('/revisi/{revision}',[DeskController::class,'update'])->name('draft.update');
    Route::post('/revisi/{revision}/kirim',[DeskController::class,'submit'])->name('submit');
    Route::get('/revisi/{revision}/pratinjau',[DeskController::class,'preview'])->name('preview');
    Route::post('/naskah/{article}/revisi',[DeskController::class,'revise'])->name('revise');
    Route::get('/antrean',[DeskController::class,'queue'])->name('queue');
    Route::post('/revisi/{revision}/putusan',[DeskController::class,'decide'])->name('decide');
    Route::post('/naskah/{article}/tarik',[DeskController::class,'withdraw'])->name('withdraw');
    Route::post('/naskah/{article}/headline',[DeskController::class,'feature'])->name('feature');
    Route::get('/pengguna',[AdminController::class,'users'])->name('users');
    Route::post('/pengguna',[AdminController::class,'createUser'])->name('users.store');
    Route::post('/pengguna/{user}/status',[AdminController::class,'toggle'])->name('users.toggle');
    Route::get('/pengaturan',[AdminController::class,'settings'])->name('settings');
    Route::put('/pengaturan',[AdminController::class,'saveSettings'])->name('settings.save');
});
