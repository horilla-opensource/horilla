import json

from django.core.management.base import BaseCommand

from helpdesk.models import FAQ, FAQCategory


class Command(BaseCommand):
    help = "Create FAQ categories and FAQs from a JSON file"

    def add_arguments(self, parser):
        parser.add_argument(
            "file_path",
            type=str,
            help="The path to the JSON file containing FAQ categories and FAQs",
        )

    def handle(self, *args, **kwargs):
        file_path = kwargs["file_path"]

        try:
            with open(file_path, "r") as file:
                data_dict = json.load(file)

                faq_categories = data_dict.get("FAQ_CATEGORY", [])
                faqs = data_dict.get("FAQS", [])

                for category_data in faq_categories:
                    title = category_data.get("title")
                    description = category_data.get("description")
                    category, created = FAQCategory.objects.get_or_create(
                        title=title, defaults={"description": description}
                    )
                    if not created:
                        category.description = description
                        category.save()

                for faq_data in faqs:
                    category_title = faq_data.get("category")
                    question = faq_data.get("question")
                    answer = faq_data.get("answer")

                    try:
                        category = FAQCategory.objects.get(title=category_title)
                    except FAQCategory.DoesNotExist:
                        self.stdout.write(
                            self.style.ERROR(
                                f'Category "{category_title}" does not exist. Skipping FAQ: {question}'
                            )
                        )
                        continue

                    FAQ.objects.get_or_create(
                        question=question,
                        defaults={
                            "answer": answer,
                            "category": category,
                        },
                    )
                self.stdout.write(
                    self.style.SUCCESS("Successfully created FAQs and FAQ categories.")
                )

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Invalid JSON format: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
