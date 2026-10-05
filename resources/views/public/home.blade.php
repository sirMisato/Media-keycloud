@extends('layouts.public')
@section('content')
<div class="wrap">
    <div class="topic-line"><strong>DARI PESANTREN, UNTUK UMAT</strong><span>Fiqih yang dekat dengan kehidupan.</span><a href="{{ route('institution') }}">Mengenal Ma’had Aly <x-icon name="arrow"/></a></div>
    @if($lead)
    @php($lr=$lead->publishedRevision)
    <div class="front-grid">
        <section class="lead-story" aria-label="Pilihan redaksi">
            <a href="{{ route('article',$lead->slug) }}" class="lead-photo" tabindex="-1" aria-hidden="true">
                @if($lr->coverUrl())<img src="{{ $lr->coverUrl() }}" alt="" width="800" height="480" fetchpriority="high">
                @else<div class="lead-placeholder"><x-icon name="book"/><span>{{ $lr->category->name }}</span></div>@endif
                <span class="lead-badge">PILIHAN REDAKSI</span>
            </a>
            <div class="lead-text"><a class="eyebrow" href="{{ route('channel',$lr->category->slug) }}">{{ $lr->category->name }}</a><h1><a href="{{ route('article',$lead->slug) }}">{{ $lr->title }}</a></h1><p>{{ $lr->excerpt }}</p><div class="meta"><span class="author-dot">{{ mb_substr($lead->author->name,0,1) }}</span><span>{{ $lead->author->name }} <span class="meta-separator">·</span> <time datetime="{{ $lead->published_at->toAtomString() }}">{{ $lead->published_at->translatedFormat('d M Y') }}</time></span></div></div>
        </section>
        <aside class="front-aside">
            <div class="section-heading"><h2>Sorotan</h2><span class="tiny-label">PILIHAN BACAAN</span></div>
            @forelse($articles->where('id','!=',$lead->id)->take(3) as $item)
            <article class="side-story"><span class="story-number" aria-hidden="true">{{ str_pad($loop->iteration,2,'0',STR_PAD_LEFT) }}</span><div><a class="eyebrow" href="{{ route('channel',$item->publishedRevision->category->slug) }}">{{ $item->publishedRevision->category->name }}</a><h3><a href="{{ route('article',$item->slug) }}">{{ $item->publishedRevision->title }}</a></h3><div class="meta">{{ $item->published_at->translatedFormat('d M Y') }} · {{ $item->publishedRevision->readingMinutes() }} menit baca</div></div></article>
            @empty<p class="aside-note">Ikuti kajian dan kabar berikutnya dari ruang redaksi.</p>@endforelse
            <a class="campus-small" href="{{ route('institution') }}"><x-icon name="school"/><span><small>LEMBAGA KAMI</small><strong>Ma’had Aly Situbondo</strong><span>Kenali pendidikan & keilmuannya</span></span><x-icon name="arrow"/></a>
        </aside>
    </div>
    @if($articles->where('id','!=',$lead->id)->isNotEmpty())
    <section class="latest-section" aria-labelledby="latest-title"><div class="section-heading"><h2 id="latest-title">Warta & gagasan terbaru</h2><a href="{{ route('articles') }}">Lihat semua <x-icon name="arrow"/></a></div><div class="cards">@foreach($articles->where('id','!=',$lead->id)->take(9) as $item)@include('components.card')@endforeach</div></section>
    @endif
    @else
    <section class="empty-public"><span class="eyebrow">MEDIA MA’HAD ALY SITUBONDO</span><h1>Merawat tradisi.<br>Menjawab zaman.</h1><p>{{ $site['about'] }}</p><div class="empty-note">Naskah pertama sedang disiapkan oleh redaksi.</div><a class="button" href="{{ route('institution') }}">Mengenal Ma’had Aly <x-icon name="arrow"/></a></section>
    @endif
    <section class="institution-banner" aria-labelledby="campus-title">
        <div class="institution-seal" aria-hidden="true"><x-icon name="school"/><span>SUKOREJO<br>SITUBONDO</span></div>
        <div class="institution-copy"><span class="eyebrow">BERAKAR PADA TRADISI KEILMUAN PESANTREN</span><h2 id="campus-title">Dari ruang belajar,<br>untuk kemaslahatan umat.</h2><p>Mengenal Ma’had Aly Salafiyah Syafi’iyah Situbondo: pendidikan tinggi pesantren dengan takhassus fikih dan usul fikih.</p><a href="{{ route('institution') }}">Jelajahi profil pendidikan <x-icon name="arrow"/></a></div>
        <span class="institution-word" lang="ar" dir="rtl" aria-hidden="true">العلم</span>
    </section>
    <section class="channel-strip" id="kanal" aria-labelledby="channel-title"><div><span class="eyebrow">JENDELA KEILMUAN</span><h2 id="channel-title">Banyak sudut pandang.<br>Satu ruang belajar.</h2><p>Temukan bacaan sesuai ketertarikan Anda.</p></div><div class="channel-links">@foreach($channels as $c)<a href="{{ route('channel',$c->slug) }}"><span>{{ $c->name }}</span><x-icon name="arrow"/></a>@endforeach</div></section>
    <section class="app-promo" data-install-area aria-labelledby="app-title"><span class="app-promo-icon"><x-icon name="phone"/></span><div><h2 id="app-title">Teman baca, di mana saja.</h2><p>Akses media Ma’had Aly langsung dari layar utama ponsel Anda.</p></div><button type="button" class="button" data-install><x-icon name="download"/> Pasang aplikasi</button></section>
    <section class="contributor-strip"><div><span class="eyebrow">RUANG KONTRIBUSI</span><h2>Gagasan baik layak dibagikan.</h2><p>Mari menulis, merawat nalar, dan memperluas manfaat.</p></div><a class="button outline" href="{{ route('page','pedoman') }}">Panduan menulis <x-icon name="arrow"/></a></section>
</div>
@endsection
