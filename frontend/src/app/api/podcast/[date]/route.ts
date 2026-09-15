import fs from "fs";
import path from "path";
import { NextRequest, NextResponse } from "next/server";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ date: string }> }
) {
  try {
    const { date } = await params;
    const sanitizedDate = date.replace(/[^0-9-]/g, "");
    const podcastPath = path.resolve(
      process.cwd(),
      "..",
      "edicoes",
      "podcasts",
      `podcast_${sanitizedDate}.mp3`
    );

    if (!fs.existsSync(podcastPath)) {
      return new NextResponse("Podcast not found for this date", { status: 404 });
    }

    const stat = fs.statSync(podcastPath);
    const stream = fs.createReadStream(podcastPath);

    // ReadableStream for web response
    const webStream = new ReadableStream({
      start(controller) {
        stream.on("data", (chunk) => controller.enqueue(chunk));
        stream.on("end", () => controller.close());
        stream.on("error", (err) => controller.error(err));
      },
      cancel() {
        stream.destroy();
      },
    });

    return new NextResponse(webStream, {
      status: 200,
      headers: {
        "Content-Type": "audio/mpeg",
        "Content-Length": stat.size.toString(),
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=3600",
      },
    });
  } catch (error) {
    console.error("Podcast stream error:", error);
    return new NextResponse("Internal server error", { status: 500 });
  }
}
