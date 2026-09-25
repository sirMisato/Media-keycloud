<?php
namespace App\Http\Controllers;
use App\Models\{Article,Category,Revision,Setting};
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
class PublicController extends Controller {
    private function live() { return Article::live()->with(['author','publishedRevision.category'])->latest('published_at'); }
    public function home() {
        $articles=$this->live()->orderByDesc('id')->limit(15)->get();
        $lead=$articles->firstWhere('featured',true) ?? $articles->first();
        return view('public.home',compact('articles','lead'));
    }
    public function index(Request $request,?string $slug=null) {
        $request->validate(['q'=>'nullable|string|max:120']);
        $category=$slug ? Category::where('slug',$slug)->firstOrFail() : null;
        $q=trim($request->string('q')->toString());
        $articles=$this->live()->when($category,fn ($query) => $query->whereHas('publishedRevision',fn ($r) => $r->where('category_id',$category->id)))
            ->when($q,fn ($query) => $query->whereHas('publishedRevision',fn ($r) => $r->where(fn ($s) => $s->where('title','like','%'.$q.'%')->orWhere('excerpt','like','%'.$q.'%'))))
            ->paginate(12)->withQueryString();
        return view('public.index',compact('articles','category','q'));
    }
    public function article(string $slug) {
        $article=$this->live()->where('slug',$slug)->firstOrFail(); $revision=$article->publishedRevision;
        $related=$this->live()->where('id','!=',$article->id)->whereHas('publishedRevision',fn ($q) => $q->where('category_id',$revision->category_id))->limit(3)->get();
        return view('public.article',compact('article','revision','related'));
    }
    public function page(string $page) {
        abort_unless(in_array($page,['tentang','pedoman','privasi']),404);
        return view('public.page',['page'=>$page,'settings'=>Setting::values()]);
    }
    public function cover(Request $request,string $path) {
        abort_unless(preg_match('/^[A-Za-z0-9._-]+$/D',$path),404);
        $key='covers/'.$path;
        $public=Revision::where('cover_path',$key)->where('status','published')->whereHas('article',fn ($q) => $q->live()->whereColumn('articles.published_revision_id','revisions.id'))->exists();
        $logo=Setting::where('key','logo')->value('value') === $key;
        $private=$request->user()?->active && Revision::where('cover_path',$key)->whereHas('article',function ($q) use ($request) {
            if (!$request->user()->isAdmin()) $q->where('author_id',$request->user()->id);
        })->exists();
        abort_unless(($public || $private || $logo) && Storage::disk('local')->exists($key),404);
        return response()->file(Storage::disk('local')->path($key),['Cache-Control'=>'private, no-store']);
    }
    public function robots() {
        $body=config('media.noindex') ? "User-agent: *\nDisallow: /\n" : "User-agent: *\nDisallow: /redaksi\nDisallow: /masuk\nSitemap: ".url('/sitemap.xml')."\n";
        return response($body)->header('Content-Type','text/plain');
    }
    public function sitemap() {
        $urls=config('media.noindex') ? collect() : $this->live()->limit(45000)->get();
        return response()->view('public.sitemap',compact('urls'))->header('Content-Type','application/xml');
    }
}
