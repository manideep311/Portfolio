from django.test import TestCase

from portfolio.pages import PAGES

from .helpers import TempMediaMixin, make_profile, make_project


class NotebookPageTests(TempMediaMixin, TestCase):
    def setUp(self):
        make_profile()

    def test_every_page_renders_with_one_h1_and_its_tab_marked(self):
        for page in PAGES:
            with self.subTest(page=page.key):
                response = self.client.get(page.url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content.decode().count("<h1"), 1)
                if page.key != "home":
                    self.assertContains(response, f'<a href="{page.url}" aria-current="page">')

    def test_pager_links_neighbouring_pages(self):
        response = self.client.get("/about/")
        self.assertContains(response, 'href="/work/" rel="prev"')
        self.assertContains(response, 'href="/toolkit/" rel="next"')
        self.assertContains(response, 'data-page-order="2"')

    def test_cover_and_last_page_have_one_neighbour(self):
        cover = self.client.get("/")
        self.assertNotContains(cover, 'rel="prev"')
        self.assertContains(cover, 'href="/work/" rel="next"')
        last = self.client.get("/contact/")
        self.assertContains(last, 'href="/playground/" rel="prev"')
        self.assertNotContains(last, 'rel="next"')

    def test_case_study_turns_back_to_work(self):
        project = make_project(title="Deep Dive")
        response = self.client.get(project.get_absolute_url())
        self.assertContains(response, 'href="/work/" rel="prev"')
        self.assertContains(response, 'href="/about/" rel="next"')
        self.assertContains(response, 'data-page-order="1.5"')
        self.assertContains(response, '<a href="/work/" aria-current="page">')

    def test_neighbours_are_prefetched(self):
        response = self.client.get("/toolkit/")
        self.assertContains(response, '<link rel="prefetch" href="/about/">')
        self.assertContains(response, '<link rel="prefetch" href="/journey/">')

    def test_unknown_pages_have_no_pager(self):
        response = self.client.get("/no-such-page/")
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, 'class="pager"', status_code=404)

    def test_sitemap_lists_every_page(self):
        response = self.client.get("/sitemap.xml")
        for page in PAGES:
            self.assertContains(response, f"<loc>http://testserver{page.url}</loc>")


class LeafTests(TempMediaMixin, TestCase):
    def setUp(self):
        make_profile()

    def test_leaf_of_groups_items(self):
        from portfolio.templatetags.notebook import leaf_of

        self.assertEqual([leaf_of(i, 3) for i in range(7)], [1, 1, 1, 2, 2, 2, 3])

    def test_dense_pages_are_split_into_leaves(self):
        response = self.client.get("/")
        self.assertContains(response, 'data-leaf="1"')
        self.assertContains(response, 'data-leaf="2"')
        self.assertContains(response, "data-leaf-status")

    def test_case_study_without_screenshots_has_three_leaves(self):
        project = make_project(title="Leafy")
        body = self.client.get(project.get_absolute_url()).content.decode()
        self.assertIn('data-leaf="3"', body)
        self.assertNotIn('data-leaf="4"', body)
