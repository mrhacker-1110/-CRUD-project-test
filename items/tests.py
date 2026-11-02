from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .forms import ItemForm
from .models import Item


class ItemModelTests(TestCase):
    """Тесты модели."""

    def test_str_returns_name(self):
        item = Item.objects.create(name='Ноутбук', price=Decimal('500.00'))
        self.assertEqual(str(item), 'Ноутбук')

    def test_get_absolute_url(self):
        item = Item.objects.create(name='Мышь', price=Decimal('10.00'))
        self.assertEqual(item.get_absolute_url(), reverse('items:detail', args=[item.pk]))

    def test_description_is_optional(self):
        item = Item.objects.create(name='Клавиатура', price=Decimal('20.00'))
        self.assertEqual(item.description, '')

    def test_ordering_newest_first(self):
        first = Item.objects.create(name='Первый', price=1)
        second = Item.objects.create(name='Второй', price=2)
        self.assertEqual(list(Item.objects.all()), [second, first])


class ItemFormTests(TestCase):
    """Тесты формы (валидация)."""

    def test_valid_form(self):
        form = ItemForm(data={'name': 'Тест', 'description': 'Описание', 'price': '9.99'})
        self.assertTrue(form.is_valid())

    def test_name_required(self):
        form = ItemForm(data={'name': '', 'price': '5'})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_price_required(self):
        form = ItemForm(data={'name': 'Тест'})
        self.assertFalse(form.is_valid())
        self.assertIn('price', form.errors)

    def test_negative_price_invalid(self):
        form = ItemForm(data={'name': 'Тест', 'price': '-1'})
        self.assertFalse(form.is_valid())
        self.assertIn('price', form.errors)

    def test_name_too_long(self):
        form = ItemForm(data={'name': 'a' * 101, 'price': '5'})
        self.assertFalse(form.is_valid())

    def test_price_not_a_number(self):
        form = ItemForm(data={'name': 'Тест', 'price': 'abc'})
        self.assertFalse(form.is_valid())


class ItemCreateTests(TestCase):
    """C — Create."""

    def test_get_create_page(self):
        response = self.client.get(reverse('items:create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'items/item_form.html')

    def test_create_item_success(self):
        response = self.client.post(reverse('items:create'), {
            'name': 'Телефон', 'description': 'Смартфон', 'price': '300.00'})
        self.assertEqual(Item.objects.count(), 1)
        item = Item.objects.first()
        self.assertRedirects(response, item.get_absolute_url())
        self.assertEqual(item.name, 'Телефон')
        self.assertEqual(item.price, Decimal('300.00'))

    def test_create_item_invalid_data(self):
        response = self.client.post(reverse('items:create'), {'name': '', 'price': '10'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Item.objects.count(), 0)
        self.assertTrue(response.context['form'].errors)

    def test_create_item_negative_price(self):
        self.client.post(reverse('items:create'), {'name': 'X', 'price': '-5'})
        self.assertEqual(Item.objects.count(), 0)


class ItemReadTests(TestCase):
    """R — Read (list + detail)."""

    @classmethod
    def setUpTestData(cls):
        cls.item = Item.objects.create(name='Планшет', description='10 дюймов', price=Decimal('150.00'))

    def test_list_page(self):
        response = self.client.get(reverse('items:list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'items/item_list.html')
        self.assertContains(response, 'Планшет')
        self.assertIn(self.item, response.context['items'])

    def test_list_empty(self):
        Item.objects.all().delete()
        response = self.client.get(reverse('items:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Список пуст')

    def test_detail_page(self):
        response = self.client.get(reverse('items:detail', args=[self.item.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'items/item_detail.html')
        self.assertContains(response, '10 дюймов')
        self.assertEqual(response.context['item'], self.item)

    def test_detail_404(self):
        response = self.client.get(reverse('items:detail', args=[9999]))
        self.assertEqual(response.status_code, 404)


class ItemUpdateTests(TestCase):
    """U — Update."""

    def setUp(self):
        self.item = Item.objects.create(name='Старое', description='old', price=Decimal('10.00'))
        self.url = reverse('items:update', args=[self.item.pk])

    def test_get_update_page_prefilled(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form'].instance, self.item)
        self.assertContains(response, 'Старое')

    def test_update_success(self):
        response = self.client.post(self.url, {'name': 'Новое', 'description': 'new', 'price': '25.50'})
        self.assertRedirects(response, self.item.get_absolute_url())
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, 'Новое')
        self.assertEqual(self.item.price, Decimal('25.50'))

    def test_update_invalid_does_not_change(self):
        response = self.client.post(self.url, {'name': '', 'price': '25'})
        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, 'Старое')

    def test_update_404(self):
        response = self.client.post(reverse('items:update', args=[9999]), {'name': 'X', 'price': '1'})
        self.assertEqual(response.status_code, 404)


class ItemDeleteTests(TestCase):
    """D — Delete."""

    def setUp(self):
        self.item = Item.objects.create(name='Удалить', price=Decimal('1.00'))
        self.url = reverse('items:delete', args=[self.item.pk])

    def test_get_confirm_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'items/item_confirm_delete.html')
        self.assertEqual(Item.objects.count(), 1)  # GET ничего не удаляет

    def test_delete_success(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('items:list'))
        self.assertFalse(Item.objects.filter(pk=self.item.pk).exists())

    def test_delete_404(self):
        response = self.client.post(reverse('items:delete', args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_delete_only_target(self):
        other = Item.objects.create(name='Остаётся', price=Decimal('2.00'))
        self.client.post(self.url)
        self.assertTrue(Item.objects.filter(pk=other.pk).exists())


class ItemFullCycleTest(TestCase):
    """Сквозной сценарий: create -> read -> update -> delete."""

    def test_full_crud_cycle(self):
        self.client.post(reverse('items:create'), {'name': 'Цикл', 'description': 'd', 'price': '5'})
        item = Item.objects.get(name='Цикл')

        self.assertEqual(self.client.get(item.get_absolute_url()).status_code, 200)

        self.client.post(reverse('items:update', args=[item.pk]), {'name': 'Цикл2', 'description': 'd', 'price': '6'})
        item.refresh_from_db()
        self.assertEqual(item.name, 'Цикл2')

        self.client.post(reverse('items:delete', args=[item.pk]))
        self.assertEqual(Item.objects.count(), 0)
