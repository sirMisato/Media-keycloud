@props(['name'])
<svg {{ $attributes->merge(['class'=>'icon']) }} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
@switch($name)
@case('home')<path d="m3 10 9-7 9 7v10H3Z"/><path d="M9 20v-7h6v7"/>@break
@case('search')<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>@break
@case('menu')<path d="M4 6h16M4 12h16M4 18h16"/>@break
@case('grid')<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>@break
@case('book')<path d="M12 5c-3-2-6-2-10-1v15c4-1 7-1 10 1 3-2 6-2 10-1V4c-4-1-7-1-10 1Zm0 0v15"/>@break
@case('school')<path d="m2 8 10-5 10 5-10 5Zm4 3v6c4 3 8 3 12 0v-6M22 8v8"/>@break
@case('arrow')<path d="M4 12h16m-6-6 6 6-6 6"/>@break
@case('external')<path d="M14 3h7v7M10 14 21 3M10 3H3v18h18v-7"/>@break
@case('download')<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>@break
@case('close')<path d="m6 6 12 12M6 18 18 6"/>@break
@case('phone')<rect x="6" y="2" width="12" height="20" rx="3"/><path d="M10 5h4M11 19h2"/>@break
@case('share')<path d="M12 16V2m-4 4 4-4 4 4M6 10H3v12h18V10h-3"/>@break
@endswitch
</svg>
