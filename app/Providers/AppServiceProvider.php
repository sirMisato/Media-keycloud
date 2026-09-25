<?php
namespace App\Providers;
use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\{URL,View};
use Illuminate\Pagination\Paginator;
class AppServiceProvider extends ServiceProvider {
    public function register(): void {}
    public function boot(): void {
        \Carbon\Carbon::setLocale('id');
        Paginator::defaultView('components.pagination');
        if (str_starts_with(config('app.url'),'https://')) URL::forceScheme('https');
        View::composer(['layouts.*'],function ($view) {
            $view->with('site',\App\Models\Setting::values());
            $view->with('channels',\App\Models\Category::orderBy('id')->get());
        });
    }
}
