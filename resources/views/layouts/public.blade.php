<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>@yield('title', $site['name'].' '.$site['location'])</title><meta name="description" content="@yield('description', $site['about'])">
<meta name="theme-color" content="#123b2d"><link rel="manifest" href="/manifest.webmanifest"><link rel="icon" href="/icons/icon-192.png"><link rel="apple-touch-icon" href="/icons/icon-192.png">
<link rel="canonical" href="{{ url()->current() }}"><meta property="og:title" content="@yield('title', $site['name'].' '.$site['location'])"><meta property="og:description" content="@yield('description', $site['about'])"><meta property="og:type" content="@yield('ogtype', 'website')"><meta property="og:url" content="{{ url()->current() }}">
@hasSection('ogimage')<meta property="og:image" content="@yield('ogimage')">
@endif
@if(config('media.noindex'))<meta name="robots" content="noindex,nofollow">
@endif
<link rel="stylesheet" href="/assets/app.css"><script src="/assets/app.js" defer></script></head>
<body><a class="skip" href="#content">Langsung ke konten</a>
<div class="topline"><div class="wrap top-inner"><span>{{ now()->translatedFormat('l, d F Y') }} <span class="muted-dot">•</span> {{ $site['location'] }}, Jawa Timur</span><div><a href="{{ route('page','tentang') }}">Tentang kami</a><a href="{{ route('login') }}">Ruang redaksi ↗</a></div></div></div>
<header class="wrap masthead"><a href="/" class="brand" aria-label="Beranda {{ $site['name'] }}">
@if(!empty($site['logo']))<img class="brand-logo" src="{{ route('cover',basename($site['logo'])) }}" alt="Logo media">@else<span class="brand-mark" aria-hidden="true">م</span>
@endif
<span><strong>{{ $site['name'] }}<span class="brand-place">{{ $site['location'] }}</span></strong><small>{{ $site['tagline'] }}</small></span></a>
<div class="masthead-right"><span class="edition">MEDIA ISLAM & KAJIAN PESANTREN</span><form action="{{ route('articles') }}" class="search"><label class="sr" for="search">Cari artikel</label><input id="search" name="q" placeholder="Cari kajian, gagasan, kabar…" maxlength="120" value="{{ request('q') }}"><button aria-label="Cari">⌕</button></form></div></header>
<nav class="main-nav" aria-label="Kanal utama"><div class="wrap nav-inner"><a href="/" @class(['active'=>request()->routeIs('home')])>Beranda</a>@foreach($channels as $c)<a href="{{ route('channel',$c->slug) }}" @class(['active'=>request()->is('kanal/'.$c->slug)])>{{ $c->name }}</a>@endforeach<a class="all-link" href="{{ route('articles') }}">Semua artikel ↗</a></div></nav>
@if(config('media.demo'))<div class="demo-bar">VERSI DEVELOPMENT · Artikel dan ilustrasi contoh untuk pengujian; bukan publikasi atau fatwa lembaga.</div>
@endif
<main id="content">@yield('content')</main>
<footer><div class="wrap footer-grid"><div><a href="/" class="footer-brand">{{ $site['name'] }} <span>{{ $site['location'] }}</span></a><p>{{ $site['about'] }}</p><small>© {{ date('Y') }} {{ $site['name'] }} {{ $site['location'] }}</small></div><div><h3>Jelajahi kanal</h3>@foreach($channels as $c)<a href="{{ route('channel',$c->slug) }}">{{ $c->name }}</a>@endforeach</div><div><h3>Ruang bersama</h3><a href="{{ route('page','tentang') }}">Tentang & redaksi</a><a href="{{ route('page','pedoman') }}">Pedoman kontribusi</a><a href="{{ route('page','privasi') }}">Privasi</a><a href="{{ route('login') }}">Masuk kontributor</a><button type="button" class="install-button" data-install hidden>Pasang aplikasi ↗</button></div></div></footer>
</body></html>
