@extends('layouts.public')
@section('content')
<div class="wrap"><div class="topic-line"><strong>RUANG GAGASAN</strong><span>Fiqih yang dekat dengan kehidupan.</span><a href="{{ route('channel','fiqih-kontemporer') }}">Jelajahi kajian <span>→</span></a></div>
@if($lead)
@php($lr=$lead->publishedRevision)
<div class="front-grid"><section class="lead-story" aria-label="Pilihan redaksi">
<a href="{{ route('article',$lead->slug) }}" class="lead-photo">@if($lr->coverUrl())<img src="{{ $lr->coverUrl() }}" alt="{{ $lr->cover_caption ?: 'Ilustrasi kajian pesantren' }}" fetchpriority="high">@else<div class="lead-placeholder">{{ $site['name'] }}</div>@endif<span class="lead-badge">PILIHAN REDAKSI</span></a>
<div class="lead-text"><a class="eyebrow" href="{{ route('channel',$lr->category->slug) }}">{{ $lr->category->name }}</a><h1><a href="{{ route('article',$lead->slug) }}">{{ $lr->title }}</a></h1><p>{{ $lr->excerpt }}</p><div class="meta"><span class="author-dot">{{ mb_substr($lead->author->name,0,1) }}</span>{{ $lead->author->name }} <span>·</span> {{ $lead->published_at->translatedFormat('d M Y') }}</div></div></section>
<aside class="front-aside"><div class="section-heading"><h2>Sorotan</h2><span class="tiny-label">DARI MEJA REDAKSI</span></div>
@foreach($articles->where('id','!=',$lead->id)->take(3) as $item)<article class="side-story"><a class="eyebrow" href="{{ route('channel',$item->publishedRevision->category->slug) }}">{{ $item->publishedRevision->category->name }}</a><h3><a href="{{ route('article',$item->slug) }}">{{ $item->publishedRevision->title }}</a></h3><div class="meta">{{ $item->published_at->translatedFormat('d M Y') }} · {{ $item->publishedRevision->readingMinutes() }} menit baca</div></article>@endforeach
<div class="contribution"><span class="tiny-label">DARI PESANTREN, UNTUK UMAT</span><h3>Gagasan baik layak dibagikan.</h3><p>Mari menulis, merawat nalar, dan memperluas manfaat.</p><a href="{{ route('page','pedoman') }}">Panduan menjadi kontributor →</a></div></aside></div>
<section class="latest-section"><div class="section-heading"><h2>Warta & gagasan terbaru</h2><a href="{{ route('articles') }}">Lihat semua →</a></div><div class="cards">@foreach($articles->where('id','!=',$lead->id)->take(6) as $item)@include('components.card')@endforeach</div></section>
@else
<section class="empty-public"><span class="eyebrow">SELAMAT DATANG DI {{ mb_strtoupper($site['name']) }}</span><h1>Merawat tradisi.<br>Menjawab zaman.</h1><p>{{ $site['about'] }}</p><div class="empty-note">Naskah pertama sedang disiapkan oleh redaksi.</div><a class="button" href="{{ route('page','tentang') }}">Mengenal media kami →</a></section>
@endif
<section class="channel-strip"><div><span class="eyebrow">JENDELA KEILMUAN</span><h2>Menelusuri khazanah,<br>membaca kehidupan.</h2></div><div class="channel-links">@foreach($channels as $c)<a href="{{ route('channel',$c->slug) }}"><span>{{ $c->name }}</span>↗</a>@endforeach</div></section>
</div>@endsection
