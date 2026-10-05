<!doctype html>
<html lang="id">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
    <title>@yield('title', $site['name'].' '.$site['location'])</title>
    <meta name="description" content="@yield('description', $site['about'])">
    <meta name="theme-color" content="#123b2d">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="Ma’had Aly">
    <link rel="manifest" href="/manifest.webmanifest">
    <link rel="icon" href="/icons/icon-192.png">
    <link rel="apple-touch-icon" href="/icons/icon-192.png">
    <link rel="canonical" href="{{ url()->current() }}">
    <meta property="og:title" content="@yield('title', $site['name'].' '.$site['location'])">
    <meta property="og:description" content="@yield('description', $site['about'])">
    <meta property="og:type" content="@yield('ogtype', 'website')">
    <meta property="og:url" content="{{ url()->current() }}">
    @hasSection('ogimage')<meta property="og:image" content="@yield('ogimage')">@endif
    @if(config('media.noindex'))<meta name="robots" content="noindex,nofollow">@endif
    <link rel="stylesheet" href="/assets/app.css?v={{ substr(hash_file('sha256', public_path('assets/app.css')),0,12) }}">
    <link rel="stylesheet" href="/assets/media.css?v={{ substr(hash_file('sha256', public_path('assets/media.css')),0,12) }}">
    <script src="/assets/app.js?v={{ substr(hash_file('sha256', public_path('assets/app.js')),0,12) }}" defer></script>
</head>
<body class="public-body">
<a class="skip" href="#content">Langsung ke konten</a>
<div class="topline"><div class="wrap top-inner">
    <span>{{ now()->translatedFormat('l, d F Y') }} <span class="muted-dot">•</span> {{ $site['location'] }}, Jawa Timur</span>
    <div><a href="{{ route('institution') }}">Profil pendidikan</a><a href="{{ route('login') }}">Ruang redaksi ↗</a></div>
</div></div>
<div class="public-header">
    <header class="wrap masthead">
        <a href="{{ route('home') }}" class="brand" aria-label="Beranda {{ $site['name'] }}">
            @if(!empty($site['logo']))<img class="brand-logo" src="{{ route('cover',basename($site['logo'])) }}" alt="Logo media" width="60" height="60">
            @else<span class="brand-mark" aria-hidden="true">م</span>@endif
            <span><strong>{{ $site['name'] }}</strong><span class="brand-place">{{ $site['location'] }}</span><small>{{ $site['tagline'] }}</small></span>
        </a>
        <div class="masthead-right">
            <span class="edition">MEDIA ISLAM & KAJIAN PESANTREN</span>
            <form action="{{ route('articles') }}" class="search" role="search">
                <label class="sr" for="header-search">Cari artikel</label>
                <input id="header-search" type="search" name="q" placeholder="Cari kajian, gagasan, kabar…" maxlength="120" value="{{ is_string(request('q')) ? request('q') : '' }}">
                <button aria-label="Cari artikel"><x-icon name="search"/></button>
            </form>
        </div>
        <div class="mobile-actions">
            <a class="icon-button" href="{{ route('articles') }}#pencarian" data-open-dialog="search-dialog" aria-label="Buka pencarian"><x-icon name="search"/></a>
            <a class="icon-button" href="{{ route('home') }}#kanal" data-open-dialog="menu-dialog" aria-label="Buka menu"><x-icon name="menu"/></a>
        </div>
    </header>
    <nav class="main-nav" aria-label="Kanal utama"><div class="wrap nav-inner">
        <a href="{{ route('home') }}" @class(['active'=>request()->routeIs('home')]) @if(request()->routeIs('home')) aria-current="page" @endif>Beranda</a>
        @foreach($channels as $c)<a href="{{ route('channel',$c->slug) }}" @class(['active'=>request()->is('kanal/'.$c->slug)]) @if(request()->is('kanal/'.$c->slug)) aria-current="page" @endif>{{ $c->name }}</a>@endforeach
        <a class="all-link" href="{{ route('institution') }}" @if(request()->routeIs('institution')) aria-current="page" @endif>Profil Ma’had Aly <x-icon name="arrow"/></a>
    </div></nav>
</div>
@if(config('media.demo'))<div class="demo-bar">VERSI DEVELOPMENT · Artikel dan ilustrasi contoh untuk pengujian; bukan publikasi atau fatwa lembaga.</div>@endif
<main id="content" tabindex="-1">@yield('content')</main>
<footer><div class="wrap footer-grid">
    <div><a href="{{ route('home') }}" class="footer-brand">{{ $site['name'] }} <span>{{ $site['location'] }}</span></a><p>Media Ma’had Aly Salafiyah Syafi’iyah Situbondo. Merawat khazanah pesantren, menghadirkan kajian bagi kehidupan.</p><a class="footer-campus" href="{{ route('institution') }}">Mengenal lembaga kami <x-icon name="arrow"/></a><small>© {{ date('Y') }} {{ $site['name'] }} {{ $site['location'] }}</small></div>
    <div><h3>Jelajahi kanal</h3>@foreach($channels as $c)<a href="{{ route('channel',$c->slug) }}">{{ $c->name }}</a>@endforeach<a href="{{ route('articles') }}">Semua artikel</a></div>
    <div><h3>Ruang bersama</h3><a href="{{ route('institution') }}">Profil pendidikan</a><a href="{{ route('page','tentang') }}">Tentang & redaksi</a><a href="{{ route('page','pedoman') }}">Pedoman kontribusi</a><a href="{{ route('page','privasi') }}">Privasi</a><button type="button" class="install-button" data-install><x-icon name="download"/> Pasang aplikasi</button></div>
</div></footer>
<nav class="mobile-nav" aria-label="Navigasi ponsel">
    <a href="{{ route('home') }}" @if(request()->routeIs('home')) aria-current="page" @endif><x-icon name="home"/><span>Beranda</span></a>
    <a href="{{ route('home') }}#kanal" data-open-dialog="menu-dialog" @if(request()->routeIs('channel')) aria-current="page" @endif><x-icon name="grid"/><span>Kanal</span></a>
    <a href="{{ route('articles') }}#pencarian" data-open-dialog="search-dialog" @if(request()->routeIs('articles')) aria-current="page" @endif><x-icon name="search"/><span>Cari</span></a>
    <a href="{{ route('institution') }}" @if(request()->routeIs('institution')) aria-current="page" @endif><x-icon name="school"/><span>Profil</span></a>
</nav>
<dialog id="search-dialog" class="app-dialog" aria-labelledby="search-title">
    <div class="dialog-head"><h2 id="search-title">Temukan bacaan</h2><button type="button" class="icon-button" data-close-dialog aria-label="Tutup pencarian"><x-icon name="close"/></button></div>
    <form action="{{ route('articles') }}" class="dialog-search" role="search">
        <label for="dialog-query">Apa yang ingin Anda pelajari?</label>
        <div class="search"><input id="dialog-query" type="search" name="q" placeholder="Fiqih, kitab, kabar pesantren…" maxlength="120" autofocus><button aria-label="Cari"><x-icon name="search"/></button></div>
    </form>
    <p class="tiny-label">JELAJAHI KANAL</p><div class="search-topics">@foreach($channels as $c)<a href="{{ route('channel',$c->slug) }}">{{ $c->name }}</a>@endforeach</div>
</dialog>
<dialog id="menu-dialog" class="app-dialog" aria-labelledby="menu-title">
    <div class="dialog-head"><h2 id="menu-title">Ruang bacaan</h2><button type="button" class="icon-button" data-close-dialog aria-label="Tutup menu"><x-icon name="close"/></button></div>
    <nav class="dialog-links" aria-label="Semua kanal">@foreach($channels as $c)<a href="{{ route('channel',$c->slug) }}"><span>{{ $c->name }}<small>{{ $c->description }}</small></span><x-icon name="arrow"/></a>@endforeach</nav>
    <div class="dialog-links compact"><a href="{{ route('articles') }}">Semua artikel <x-icon name="arrow"/></a><a href="{{ route('institution') }}">Profil Ma’had Aly <x-icon name="school"/></a><a href="{{ route('login') }}">Ruang redaksi <x-icon name="external"/></a></div>
    <button type="button" class="button" data-install><x-icon name="download"/> Pasang aplikasi</button>
</dialog>
<dialog id="install-dialog" class="app-dialog install-dialog" aria-labelledby="install-title">
    <div class="dialog-head"><span class="eyebrow">MEDIA DALAM GENGGAMAN</span><button type="button" class="icon-button" data-close-dialog aria-label="Tutup panduan pemasangan"><x-icon name="close"/></button></div>
    <img src="/icons/icon-192.png" alt="" width="64" height="64"><h2 id="install-title">Selangkah lebih dekat<br>dengan khazanah pesantren.</h2>
    <p>Tambahkan media Ma’had Aly ke layar utama agar mudah dibuka seperti aplikasi.</p>
    <div data-install-ios hidden><h3>Di iPhone atau iPad</h3><ol><li>Buka situs ini di Safari.</li><li>Ketuk menu Bagikan.</li><li>Pilih <strong>Tambah ke Layar Utama</strong>, lalu Tambah.</li></ol></div>
    <div data-install-other><h3>Di browser Anda</h3><p>Buka menu browser, lalu pilih <strong>Instal aplikasi</strong> atau <strong>Tambahkan ke layar utama</strong> jika tersedia. Di komputer, cari ikon instal di bilah alamat.</p><p>Jika dibuka dari Telegram atau aplikasi lain, pilih buka di browser terlebih dahulu.</p></div>
    <small>Artikel terbaru dan ruang redaksi memerlukan koneksi internet.</small>
</dialog>
</body>
</html>
