<?php
namespace Tests\Feature;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class PublicMediaTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        $this->seed();
        config(['media.noindex' => false]);
    }

    public function test_institution_profile_is_public_and_discoverable_without_articles(): void
    {
        $this->get('/')->assertOk()->assertSee(route('institution'))->assertSee('Naskah pertama');
        $this->get(route('institution'))->assertOk()
            ->assertSee('Profil Pendidikan Ma’had Aly')
            ->assertSee('Fiqh dan Ushul Fiqh')
            ->assertSee('https://maalysitubondo.ac.id/')
            ->assertSee(route('channel', 'fiqih-kontemporer'))
            ->assertHeader('Cache-Control', 'no-store, private');
        $this->get('/sitemap.xml')->assertOk()->assertSee(route('institution'));
        $this->get('/halaman/tentang')->assertOk()->assertSee(route('institution'));
    }

    public function test_search_has_a_working_form_without_javascript_and_keeps_channel_scope(): void
    {
        $this->get('/artikel?q=kitab')->assertOk()->assertSee('id="archive-query"', false)
            ->assertSee('value="kitab"', false)->assertSee('action="'.route('articles').'"', false);
        $this->get('/kanal/khazanah?q=kitab')->assertOk()
            ->assertSee('action="'.route('channel', 'khazanah').'"', false)
            ->assertSee('value="kitab"', false);
    }

    public function test_development_profile_stays_noindex_and_out_of_sitemap(): void
    {
        config(['media.noindex' => true]);
        $this->get(route('institution'))->assertOk()->assertHeader('X-Robots-Tag', 'noindex, nofollow')
            ->assertSee('content="noindex,nofollow"', false);
        $this->get('/sitemap.xml')->assertDontSee(route('institution'));
    }
}
