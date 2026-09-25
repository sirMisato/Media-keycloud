@php($r=$item->publishedRevision)
<article class="story-card">@if($r->coverUrl())<a class="card-image" href="{{ route('article',$item->slug) }}" tabindex="-1" aria-hidden="true"><img src="{{ $r->coverUrl() }}" loading="lazy" alt=""></a>@else<a class="card-blank" href="{{ route('article',$item->slug) }}" tabindex="-1" aria-hidden="true"><span>{{ $r->category->name }}</span></a>
@endif
<a class="eyebrow" href="{{ route('channel',$r->category->slug) }}">{{ $r->category->name }}</a><h3><a href="{{ route('article',$item->slug) }}">{{ $r->title }}</a></h3><p>{{ $r->excerpt }}</p><div class="meta">{{ $item->published_at->translatedFormat('d M Y') }} <span>·</span> {{ $r->readingMinutes() }} menit baca</div></article>
