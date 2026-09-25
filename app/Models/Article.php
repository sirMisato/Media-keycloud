<?php
namespace App\Models;
use Illuminate\Database\Eloquent\{Builder, Model};
use Illuminate\Database\Eloquent\Relations\{BelongsTo, HasMany};
class Article extends Model {
    protected $guarded = ['id'];
    protected function casts(): array { return ['published_at'=>'datetime','featured'=>'boolean']; }
    public function author(): BelongsTo { return $this->belongsTo(User::class,'author_id'); }
    public function publishedRevision(): BelongsTo { return $this->belongsTo(Revision::class,'published_revision_id'); }
    public function revisions(): HasMany { return $this->hasMany(Revision::class); }
    public function latestRevision() { return $this->hasOne(Revision::class)->latestOfMany(); }
    public function scopeLive(Builder $query): void {
        $query->whereNotNull('published_revision_id')->where('published_at','<=',now())
            ->whereHas('publishedRevision', fn ($q) => $q->where('status','published'));
    }
}
