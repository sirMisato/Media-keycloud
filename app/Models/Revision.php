<?php
namespace App\Models;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Support\Str;
class Revision extends Model {
    protected $guarded = ['id'];
    protected function casts(): array { return ['approved_at'=>'datetime','publish_at'=>'datetime']; }
    public function article(): BelongsTo { return $this->belongsTo(Article::class); }
    public function category(): BelongsTo { return $this->belongsTo(Category::class); }
    public function reviewer(): BelongsTo { return $this->belongsTo(User::class,'reviewed_by'); }
    public function editable(): bool { return in_array($this->status,['draft','changes_requested','rejected']); }
    public function html(): string {
        return Str::markdown($this->body,['html_input'=>'strip','allow_unsafe_links'=>false,'max_nesting_level'=>20]);
    }
    public function coverUrl(): ?string {
        if ($this->cover_path === 'demo:library') return asset('assets/editorial.webp');
        return $this->cover_path ? route('cover',['path'=>basename($this->cover_path)]) : null;
    }
    public function label(): string {
        return ['draft'=>'Draf','pending'=>'Menunggu review','changes_requested'=>'Perlu revisi','rejected'=>'Ditolak',
            'scheduled'=>'Terjadwal','published'=>'Tayang','superseded'=>'Arsip versi'][$this->status] ?? $this->status;
    }
    public function readingMinutes(): int { return max(1,(int) ceil(str_word_count(strip_tags($this->body))/180)); }
}
