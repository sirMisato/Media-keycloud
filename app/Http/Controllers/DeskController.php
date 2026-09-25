<?php
namespace App\Http\Controllers;
use App\Models\{Article,Revision,Category,AuditLog};
use App\Services\Editorial;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Illuminate\Validation\ValidationException;
class DeskController extends Controller {
    private function own(Request $r,Article $a): void { abort_unless($r->user()->isAdmin() || $a->author_id===$r->user()->id,403); }
    public function index(Request $r) {
        $base=Article::query()->when(!$r->user()->isAdmin(),fn ($q) => $q->where('author_id',$r->user()->id));
        $articles=(clone $base)->with(['author','latestRevision.category'])->latest('updated_at')->paginate(15);
        $pending=Revision::where('status','pending')->when(!$r->user()->isAdmin(),fn ($q) => $q->whereHas('article',fn ($a) => $a->where('author_id',$r->user()->id)))->count();
        $stats=['total'=>(clone $base)->count(),'live'=>(clone $base)->live()->count(),'pending'=>$pending];
        return view('desk.index',compact('articles','stats'));
    }
    public function create() { return view('desk.editor',['revision'=>new Revision,'article'=>null,'categories'=>Category::all()]); }
    private function data(Request $r): array {
        return $r->validate(['title'=>'required|string|min:8|max:180','category_id'=>'required|exists:categories,id',
            'excerpt'=>'required|string|min:20|max:350','body'=>'required|string|min:50|max:150000','sources'=>'nullable|string|max:10000',
            'cover'=>'nullable|file|image|mimes:jpg,jpeg,png,webp|max:5120|dimensions:max_width=8000,max_height=8000',
            'cover_caption'=>'nullable|string|max:255']);
    }
    public function store(Request $r,Editorial $editorial) {
        $data=$this->data($r); unset($data['cover']);
        if ($r->hasFile('cover')) $data['cover_path']=$r->file('cover')->store('covers','local');
        $revision=DB::transaction(function () use ($r,$data,$editorial) {
            $a=Article::create(['author_id'=>$r->user()->id,'slug'=>Str::slug($data['title']).'-'.Str::lower(Str::random(8))]);
            $rev=$a->revisions()->create([...$data,'status'=>'draft']); $editorial->log($rev,'created',$r->user()); return $rev;
        });
        return redirect()->route('editor',$revision)->with('success','Draf tersimpan. Periksa pratinjau, lalu kirim ke redaksi.');
    }
    public function edit(Request $r,Revision $revision) {
        $this->own($r,$revision->article);
        return view('desk.editor',['revision'=>$revision,'article'=>$revision->article,'categories'=>Category::all()]);
    }
    public function update(Request $r,Revision $revision,Editorial $editorial) {
        $this->own($r,$revision->article); $data=$this->data($r); unset($data['cover']);
        DB::transaction(function () use ($r,$revision,$data,$editorial) {
            $a=Article::whereKey($revision->article_id)->lockForUpdate()->firstOrFail();
            $rev=Revision::whereKey($revision->id)->lockForUpdate()->firstOrFail();
            abort_unless($rev->editable(),409,'Naskah sedang direview atau sudah disetujui.');
            if ($r->hasFile('cover')) $data['cover_path']=$r->file('cover')->store('covers','local');
            $rev->update($data); $a->touch(); $editorial->log($rev,'saved',$r->user());
        });
        return back()->with('success','Perubahan draf tersimpan.');
    }
    public function submit(Request $r,Revision $revision,Editorial $editorial) {
        $this->own($r,$revision->article);
        DB::transaction(function () use ($r,$revision,$editorial) {
            $a=Article::whereKey($revision->article_id)->lockForUpdate()->firstOrFail();
            $rev=Revision::with('category')->whereKey($revision->id)->lockForUpdate()->firstOrFail();
            abort_unless($rev->editable(),409);
            if (in_array($rev->category->slug,['fiqih-kontemporer','bahtsul-masail']) && mb_strlen(trim($rev->sources ?? ''))<10)
                throw ValidationException::withMessages(['sources'=>'Kajian fiqih dan bahtsul masail harus mencantumkan rujukan.']);
            $rev->update(['status'=>'pending','review_note'=>null]); $a->touch(); $editorial->log($rev,'submitted',$r->user());
        });
        return back()->with('success','Naskah masuk antrean review admin.');
    }
    public function revise(Request $r,Article $article,Editorial $editorial) {
        $this->own($r,$article);
        $revision=DB::transaction(function () use ($r,$article,$editorial) {
            $a=Article::whereKey($article->id)->lockForUpdate()->firstOrFail();
            $open=$a->revisions()->whereIn('status',['draft','pending','changes_requested','rejected','scheduled'])->latest('id')->first();
            if ($open) return $open;
            $source=$a->revisions()->latest('id')->firstOrFail();
            $rev=$source->replicate(['status','reviewed_by','approved_at','publish_at','review_note']);
            $rev->status='draft'; $rev->save(); $a->touch(); $editorial->log($rev,'revision_created',$r->user()); return $rev;
        });
        return redirect()->route('editor',$revision)->with('success','Revisi dapat dikerjakan di sini. Versi publik tetap sampai revisi disetujui.');
    }
    public function preview(Request $r,Revision $revision) {
        $this->own($r,$revision->article);
        $history=AuditLog::with('user')->where('article_id',$revision->article_id)->latest('id')->limit(30)->get();
        return view('desk.preview',compact('revision','history'));
    }
    public function queue(Request $r) {
        abort_unless($r->user()->isAdmin(),403);
        return view('desk.queue',['revisions'=>Revision::with(['article.author','category'])->whereIn('status',['pending','scheduled'])->oldest()->paginate(20)]);
    }
    public function decide(Request $r,Revision $revision,Editorial $editorial) {
        abort_unless($r->user()->isAdmin(),403);
        $v=$r->validate(['decision'=>'required|in:approve,changes_requested,rejected',
            'note'=>'nullable|required_unless:decision,approve|string|max:3000','publish_at'=>'nullable|date|after:now']);
        $editorial->decide($revision,$r->user(),$v['decision'],$v['note'] ?? null,$v['publish_at'] ?? null);
        return back()->with('success','Keputusan redaksi tersimpan.');
    }
    public function withdraw(Request $r,Article $article,Editorial $editorial) {
        abort_unless($r->user()->isAdmin(),403); $v=$r->validate(['note'=>'required|string|min:5|max:1000']);
        DB::transaction(function () use ($r,$article,$editorial,$v) {
            $a=Article::whereKey($article->id)->lockForUpdate()->firstOrFail();
            foreach ($a->revisions()->whereIn('status',['published','scheduled'])->get() as $rev) {
                $rev->update(['status'=>'superseded']); $editorial->log($rev,'withdrawn',$r->user(),$v['note']);
            }
            $a->update(['published_revision_id'=>null]);
        });
        return back()->with('success','Artikel ditarik dan jadwal tayangnya dibatalkan.');
    }
    public function feature(Request $r,Article $article) {
        abort_unless($r->user()->isAdmin(),403);
        $article->update(['featured'=>!$article->featured]);
        return back()->with('success','Pilihan headline diperbarui.');
    }
}
