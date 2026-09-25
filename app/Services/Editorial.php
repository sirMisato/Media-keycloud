<?php
namespace App\Services;
use App\Models\{Article,AuditLog,Revision,User};
use Illuminate\Support\Facades\DB;
use Illuminate\Validation\ValidationException;
class Editorial {
    public function log(Revision $r,string $action,?User $actor,?string $note=null): void {
        AuditLog::create(['article_id'=>$r->article_id,'revision_id'=>$r->id,'user_id'=>$actor?->id,'action'=>$action,'note'=>$note]);
    }
    public function decide(Revision $revision,User $actor,string $decision,?string $note,?string $publishAt): void {
        abort_unless($actor->isAdmin(),403);
        DB::transaction(function () use ($revision,$actor,$decision,$note,$publishAt) {
            // All mutations lock article before revision, ensuring consistent ordering.
            $article=Article::whereKey($revision->article_id)->lockForUpdate()->firstOrFail();
            $r=Revision::whereKey($revision->id)->lockForUpdate()->firstOrFail();
            if ($r->status!=='pending') throw ValidationException::withMessages(['decision'=>'Naskah sudah diproses. Muat ulang halaman.']);
            if ($decision==='approve') {
                $r->reviewed_by=$actor->id; $r->approved_at=now();
                $r->publish_at=$publishAt ? \Carbon\Carbon::parse($publishAt,'Asia/Jakarta') : now();
                $r->status='scheduled'; $r->review_note=$note; $r->save();
                $this->log($r,'approved',$actor,$note);
                if ($r->publish_at->lte(now())) $this->publishLocked($article,$r,$actor);
            } else {
                $r->update(['status'=>$decision,'review_note'=>$note,'reviewed_by'=>$actor->id]);
                $this->log($r,$decision,$actor,$note);
            }
        });
    }
    private function publishLocked(Article $article,Revision $r,?User $actor): void {
        if ($article->published_revision_id) Revision::whereKey($article->published_revision_id)->update(['status'=>'superseded']);
        $r->update(['status'=>'published']);
        $article->update(['published_revision_id'=>$r->id,'published_at'=>$article->published_at ?? now()]);
        $this->log($r,'published',$actor);
    }
    public function publishDue(): int {
        $count=0;
        Revision::where('status','scheduled')->where('publish_at','<=',now())->each(function ($revision) use (&$count) {
            DB::transaction(function () use ($revision,&$count) {
                $a=Article::whereKey($revision->article_id)->lockForUpdate()->firstOrFail();
                $r=Revision::whereKey($revision->id)->lockForUpdate()->firstOrFail();
                if ($r->status==='scheduled' && $r->publish_at->lte(now()) && $r->approved_at) {
                    $this->publishLocked($a,$r,null); $count++;
                }
            });
        });
        return $count;
    }
}
