<?php echo '<?xml version="1.0" encoding="UTF-8"?>'; ?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">@if(!config('media.noindex'))<url><loc>{{ url('/') }}</loc></url>@endif @foreach($urls as $a)<url><loc>{{ route('article',$a->slug) }}</loc><lastmod>{{ $a->publishedRevision->updated_at->toAtomString() }}</lastmod></url>@endforeach</urlset>
