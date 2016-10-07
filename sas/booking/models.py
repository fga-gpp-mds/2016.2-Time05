from django.utils.translation import ugettext_lazy as _, ugettext as __
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
import copy
from django.db import connection
from django.core.exceptions import ValidationError

CATEGORY = (('', '----'), ('1', _('Student')), ('2', _('Teaching Staff')), ('3', _('Employees')))

WEEKDAYS = (('0', _("Monday")), ('1', _("Tuesday")), ('2', _("Wednesday")),
			('3', _("Thursday")), ('4', _("Friday")), ('5', _("Saturday")),
			('6', _("Sunday")))

class Building(models.Model):
	name = models.CharField(max_length=200)

	def __str__(self):
		return self.name

class Place(models.Model):
	building = models.ForeignKey(Building, related_name='building')
	name = models.CharField(max_length=200)
	location = models.CharField(max_length=50)
	capacity = models.CharField(max_length=200)
	place_id = models.CharField(max_length=200)
	is_laboratory = models.BooleanField(default=False)

	def __str__(self):
		return self.name

	def get_buildings(self):
		return self.objects.values_list('building', flat=True)


class BookTime(models.Model):
	start_hour = models.TimeField(null=False, blank=False)
	end_hour = models.TimeField(null=False, blank=False)
	date_booking = models.DateField(null=False, blank=False)

	def add_days(self, nr_days):
		delta = timedelta(days=nr_days)
		self.date_booking = self.date_booking + delta

	def next_week_day(self, nr_weekday):
		diff_of_weekdays = self.date_booking.weekday() - nr_weekday
		if diff_of_weekdays > 0:
			self.add_days(7 - diff_of_weekdays)
		elif diff_of_weekdays < 0:
			self.add_days(diff_of_weekdays * (-1))
		else:
			self.add_days(7)

	def get_str_weekday(self):
		return self.date_booking.strftime("%A")


class Booking(models.Model):
	user = models.ForeignKey(User, related_name="bookings", on_delete=models.CASCADE)
	time = models.ManyToManyField(BookTime, related_name="booking_time")
	place = models.ForeignKey(Place, related_name="booking_place")
	name = models.CharField(max_length=50)
	start_date = models.DateField(null=False, blank=False)
	end_date = models.DateField(null=False, blank=False)

	def exists(self, start_hour, end_hour, week_days):
		str_weekdays = []
		if not week_days:
			return True
		for day in week_days:
				new_day = int(day) + 1 % 6
				str_weekdays.append("'" + str(new_day) + "'")

		str_weekdays = ",".join(str_weekdays)
		sql = """select count(*) from booking_booking_time bbt
			   inner join booking_booktime bt on bbt.booktime_id = bt.id
			   inner join booking_booking bb on bbt.booking_id = bb.id
			   inner join booking_place bp on bb.place_id = bp.id"""
		sql += " where bt.date_booking >= date('" + self.start_date.strftime("%Y-%m-%d") + "')"
		sql += " and bt.date_booking <= date('" + self.end_date.strftime("%Y-%m-%d") + "')"
		sql += " and bt.start_hour <= time('" + start_hour.strftime("%H:%M:%S") + "')"
		sql += " and bt.end_hour >= time('" + end_hour.strftime("%H:%M:%S") + "')"
		sql += " and strftime('%w',bt.date_booking) IN (" + str_weekdays + ")"
		sql += " and bp.id = '" + str(self.place.pk) + "'"

		print(sql)
		with connection.cursor() as cursor:
			cursor.execute(sql)
			row = cursor.fetchone()
		if row[0] > 0:
			return True
		else:
			return False

	def save(self, *args, **kwargs):
		self.place.is_laboratory = False
		if Place.objects.filter(name=self.place.name):
			self.place = Place.objects.get(name=self.place.name)
		else:
			self.place.save()
			self.place_id = self.place.pk
		super(Booking, self).save(*args, **kwargs)

class Validation():

	def hasNumbers(self, string):
		if any(char.isdigit() for char in string):
			return True

	def hasLetters(self, number):
		if any(char.isalpha() for char in number):
			return True

	def hasSpecialCharacters(self, string):
		for character in '@#$%^&+=/\{[]()}-_+=*!§|':
			if character in string:
				return True
