package org.shaher.reminders;

import android.content.Context;

import androidx.work.Data;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.ExistingWorkPolicy;
import androidx.work.OneTimeWorkRequest;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;

import java.util.Calendar;
import java.util.concurrent.TimeUnit;

/**
 * Called from Python (pyjnius). WorkManager stores the work in its own database, so scheduled
 * reminders survive app restarts and device reboots. Timing is "approximately on time" (it is
 * not an exact alarm, which avoids needing the exact-alarm permission).
 */
public final class ReminderScheduler {
    private ReminderScheduler() {}

    private static String workName(String key) {
        return "shaher_" + key;
    }

    private static Data data(String key, String title, String body) {
        return new Data.Builder().putString("key", key).putString("title", title)
                .putString("body", body).build();
    }

    public static void schedule(Context ctx, String key, String title, String body, long fireAtMillis) {
        long delay = Math.max(0L, fireAtMillis - System.currentTimeMillis());
        OneTimeWorkRequest request = new OneTimeWorkRequest.Builder(ReminderWorker.class)
                .setInitialDelay(delay, TimeUnit.MILLISECONDS)
                .setInputData(data(key, title, body))
                .build();
        WorkManager.getInstance(ctx).enqueueUniqueWork(workName(key), ExistingWorkPolicy.REPLACE, request);
    }

    public static void scheduleDaily(Context ctx, String key, String title, String body, int hour, int minute) {
        Calendar next = Calendar.getInstance();
        next.set(Calendar.HOUR_OF_DAY, hour);
        next.set(Calendar.MINUTE, minute);
        next.set(Calendar.SECOND, 0);
        next.set(Calendar.MILLISECOND, 0);
        if (next.getTimeInMillis() <= System.currentTimeMillis()) {
            next.add(Calendar.DAY_OF_YEAR, 1);
        }
        long delay = next.getTimeInMillis() - System.currentTimeMillis();
        PeriodicWorkRequest request = new PeriodicWorkRequest.Builder(ReminderWorker.class, 24, TimeUnit.HOURS)
                .setInitialDelay(delay, TimeUnit.MILLISECONDS)
                .setInputData(data(key, title, body))
                .build();
        WorkManager.getInstance(ctx).enqueueUniquePeriodicWork(
                workName(key), ExistingPeriodicWorkPolicy.UPDATE, request);
    }

    public static void cancel(Context ctx, String key) {
        WorkManager.getInstance(ctx).cancelUniqueWork(workName(key));
    }
}
