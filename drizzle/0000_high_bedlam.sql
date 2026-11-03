CREATE TABLE `correction_reports` (
	`id` text PRIMARY KEY NOT NULL,
	`created_at` text NOT NULL,
	`kind` text NOT NULL,
	`player` text NOT NULL,
	`corrected_name` text NOT NULL,
	`season` text NOT NULL,
	`class_name` text NOT NULL,
	`details` text NOT NULL,
	`evidence` text NOT NULL,
	`contact` text NOT NULL,
	`status` text DEFAULT 'new' NOT NULL
);
