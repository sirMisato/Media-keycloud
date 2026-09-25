<?php
namespace Tests\Feature;
use App\Models\{Article,Revision,User,Category};
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;
use Tests\TestCase;
class EditorialWorkflowTest extends TestCase {
    use RefreshDatabase;
    protected function setUp(): void { parent::setUp(); config(['media.noindex'=>false]); $this->seed(); }
    private function user(string $role='contributor'): User { $u=User::factory()->create();$u->role=$role;$u->save();return $u; }
    private function payload(array $extra=[]): array {
        return array_merge(['title'=>'Kajian fiqih kehidupan digital','category_id'=>Category::where('slug','fiqih-kontemporer')->value('id'),'excerpt'=>'Ringkasan kajian yang cukup panjang untuk dibaca.',
            'body'=>"## Pokok persoalan\n\nNaskah terverifikasi yang memerlukan persetujuan redaksi sebelum dipublikasikan.",'sources'=>'Kitab rujukan, penulis, edisi, halaman.'],$extra);
    }
    private function draft(User $u): Revision { $this->actingAs($u)->post(route('draft.store'),$this->payload())->assertRedirect();return Revision::latest('id')->firstOrFail(); }
    private function publish(User $u): Revision {
        $r=$this->draft($u);$this->actingAs($u)->post(route('submit',$r))->assertRedirect();
        $this->actingAs($this->user('admin'))->post(route('decide',$r),['decision'=>'approve'])->assertRedirect();return $r->fresh();
    }
    public function test_home_and_channels_work_before_first_publication(): void {
        $this->get('/')->assertOk()->assertSee('Naskah pertama');
        $this->get('/kanal/fiqih-kontemporer')->assertOk()->assertSee('Belum ada artikel');
        $this->get('/masuk')->assertOk();$this->get('/halaman/pedoman')->assertOk();
    }
    public function test_contributor_cannot_publish_or_inject_author_and_status(): void {
        $u=$this->user();$other=$this->user();
        $this->actingAs($u)->post(route('draft.store'),$this->payload(['author_id'=>$other->id,'status'=>'published','published_revision_id'=>99]))->assertRedirect();
        $r=Revision::first();$this->assertSame('draft',$r->status);$this->assertSame($u->id,$r->article->author_id);
        $this->post(route('decide',$r),['decision'=>'approve'])->assertForbidden();
        $this->post(route('feature',$r->article))->assertForbidden();
        $this->get('/baca/'.$r->article->slug)->assertNotFound();
    }
    public function test_approval_makes_exact_submitted_revision_public(): void {
        $u=$this->user();$r=$this->draft($u);
        $this->post(route('submit',$r))->assertRedirect();
        $this->get('/artikel?q=digital')->assertDontSee($r->title);
        $this->actingAs($this->user('admin'))->post(route('decide',$r),['decision'=>'approve'])->assertRedirect();
        $this->get('/baca/'.$r->article->slug)->assertOk()->assertSee($r->title);
        $this->assertDatabaseHas('audit_logs',['revision_id'=>$r->id,'action'=>'published']);
        $this->get('/artikel?q=digital')->assertSee($r->title);
        $this->get('/sitemap.xml')->assertSee($r->article->slug);
    }
    public function test_owners_only_can_edit_and_view_private_previews(): void {
        $r=$this->draft($this->user());$this->actingAs($this->user());
        $this->get(route('preview',$r))->assertForbidden();$this->get(route('editor',$r))->assertForbidden();
        $this->put(route('draft.update',$r),$this->payload())->assertForbidden();$this->post(route('submit',$r))->assertForbidden();
    }
    public function test_pending_revision_is_locked_and_duplicate_decision_fails(): void {
        $u=$this->user();$r=$this->draft($u);$this->post(route('submit',$r));
        $this->put(route('draft.update',$r),$this->payload(['title'=>'Tidak boleh berubah']))->assertStatus(409);
        $admin=$this->user('admin');$this->actingAs($admin)->post(route('decide',$r),['decision'=>'approve']);
        $this->post(route('decide',$r),['decision'=>'approve'])->assertSessionHasErrors('decision');
    }
    public function test_fiqih_requires_references_and_rejection_requires_note(): void {
        $u=$this->user();$this->actingAs($u)->post(route('draft.store'),$this->payload(['sources'=>'']));$r=Revision::first();
        $this->post(route('submit',$r))->assertSessionHasErrors('sources');
        $this->put(route('draft.update',$r),$this->payload());$this->post(route('submit',$r));
        $this->actingAs($this->user('admin'))->post(route('decide',$r),['decision'=>'rejected'])->assertSessionHasErrors('note');
        $this->post(route('decide',$r),['decision'=>'changes_requested','note'=>'Lengkapi halaman rujukan.'])->assertRedirect();
        $this->assertSame('changes_requested',$r->fresh()->status);
        $this->actingAs($u)->put(route('draft.update',$r),$this->payload())->assertRedirect();
        $this->post(route('submit',$r))->assertRedirect();$this->assertSame('pending',$r->fresh()->status);
    }
    public function test_revising_live_article_does_not_change_public_version_until_approved(): void {
        $u=$this->user();$old=$this->publish($u);$a=$old->article;
        $this->actingAs($u)->post(route('revise',$a))->assertRedirect();$new=Revision::latest('id')->first();
        $this->assertNotSame($old->id,$new->id);
        $this->put(route('draft.update',$new),$this->payload(['title'=>'Judul revisi yang belum disetujui']));
        $this->get('/baca/'.$a->slug)->assertSee($old->title)->assertDontSee('Judul revisi yang belum disetujui');
        $this->post(route('submit',$new));
        $this->actingAs($this->user('admin'))->post(route('decide',$new),['decision'=>'approve']);
        $this->get('/baca/'.$a->slug)->assertSee('Judul revisi yang belum disetujui');
        $this->assertSame('superseded',$old->fresh()->status);$this->assertSame($new->id,$a->fresh()->published_revision_id);
    }
    public function test_scheduled_publication_is_invisible_until_due(): void {
        $this->travelTo(now()->startOfMinute());$u=$this->user();$r=$this->draft($u);$this->post(route('submit',$r));
        $this->actingAs($this->user('admin'))->post(route('decide',$r),['decision'=>'approve','publish_at'=>now()->addHour()->format('Y-m-d\TH:i')])->assertRedirect();
        $this->get('/baca/'.$r->article->slug)->assertNotFound();$this->artisan('media:publish-due')->assertSuccessful();
        $this->assertSame('scheduled',$r->fresh()->status);$this->travel(61)->minutes();
        $this->artisan('media:publish-due')->assertSuccessful();$this->get('/baca/'.$r->article->slug)->assertOk();
        $this->artisan('media:publish-due')->assertSuccessful();$this->assertSame(1,\App\Models\AuditLog::where('action','published')->count());
    }
    public function test_private_cover_requires_owner_or_approval(): void {
        Storage::fake('local');$u=$this->user();
        $file=UploadedFile::fake()->createWithContent('cover.png',file_get_contents(public_path('icons/icon-192.png')));
        $this->actingAs($u)->post(route('draft.store'),$this->payload(['cover'=>$file]))->assertRedirect();$r=Revision::firstOrFail();
        $url=route('cover',basename($r->cover_path));$this->get($url)->assertOk();
        $this->actingAs($this->user())->get($url)->assertNotFound();
        $this->actingAs($u)->post(route('submit',$r));$this->actingAs($this->user('admin'))->post(route('decide',$r),['decision'=>'approve']);
        $this->post(route('logout'));$this->get($url)->assertOk();
    }
    public function test_malicious_html_and_unsafe_markdown_links_are_not_rendered(): void {
        $u=$this->user();$this->actingAs($u)->post(route('draft.store'),$this->payload(['body'=>'<script>alert("XSS")</script><img src=x onerror=alert(1)> [tautan](javascript:alert(1)) Paragraf naskah yang cukup panjang.']));
        $r=Revision::first();$this->assertStringNotContainsString('<script>',$r->html());
        $this->assertStringNotContainsString('onerror=',$r->html());$this->assertStringNotContainsString('href="javascript:',$r->html());
    }
    public function test_withdraw_hides_article_and_cover(): void {
        $r=$this->publish($this->user());$a=$r->article;
        $this->post(route('withdraw',$a),['note'=>'Rujukan perlu ditinjau ulang.'])->assertRedirect();
        $this->get('/baca/'.$a->slug)->assertNotFound();$this->get('/artikel')->assertDontSee($r->title);
    }
    public function test_non_admin_cannot_manage_users_or_identity(): void {
        $this->actingAs($this->user());$this->get(route('users'))->assertForbidden();$this->get(route('settings'))->assertForbidden();
        $this->post(route('users.store'),[])->assertForbidden();$this->put(route('settings.save'),[])->assertForbidden();
    }
    public function test_deactivated_users_cannot_continue_existing_session(): void {
        $u=$this->user();$this->actingAs($u);$u->active=false;$u->save();
        $this->get(route('desk'))->assertRedirect(route('login'));$this->assertGuest();
    }
    public function test_admin_can_create_contributor_but_not_disable_self(): void {
        $a=$this->user('admin');$this->actingAs($a)->post(route('users.store'),['name'=>'Penulis Baru','email'=>'baru@example.test','password'=>'LongPassword123!','password_confirmation'=>'LongPassword123!','role'=>'contributor'])->assertRedirect();
        $this->assertDatabaseHas('users',['email'=>'baru@example.test','role'=>'contributor']);
        $this->post(route('users.toggle',$a))->assertStatus(422);
    }
    public function test_desk_pages_render_with_data(): void {
        $r=$this->draft($this->user());$this->actingAs($this->user('admin'));
        foreach ([route('desk'),route('write'),route('editor',$r),route('preview',$r),route('queue'),route('settings'),route('users'),route('account')] as $url) $this->get($url)->assertOk();
    }
    public function test_demo_seed_is_denied_in_production(): void {
        $this->app->detectEnvironment(fn ()=>'production');config(['media.demo'=>true]);
        $this->expectException(\RuntimeException::class);app(\Database\Seeders\DemoSeeder::class)->run();
    }
    public function test_noindex_and_private_cache_headers(): void {
        config(['media.noindex'=>true]);$this->get('/')->assertHeader('X-Robots-Tag','noindex, nofollow')->assertHeader('Cache-Control','no-store, private');
        $this->get('/robots.txt')->assertSee('Disallow: /');$this->get('/redaksi')->assertRedirect('/masuk');
    }
    public function test_login_validates_credentials_and_logs_out(): void {
        $u=$this->user();$u->password='TestingPassword123!';$u->save();
        $this->post('/masuk',['email'=>$u->email,'password'=>'wrong'])->assertSessionHasErrors('email');
        $this->post('/masuk',['email'=>$u->email,'password'=>'TestingPassword123!'])->assertRedirect(route('desk'));$this->assertAuthenticatedAs($u);
        $this->post(route('logout'))->assertRedirect('/');$this->assertGuest();
    }
}
