#include "cv.h"
#include "highgui.h"

using namespace cv;

int main(int, char**)
{
    VideoCapture cap(0);
    if(!cap.isOpened()) return -1;

    vector<vector<Point> > contours;
    vector<Vec4i> hierarchy;

    Mat frame, edges;
    namedWindow("edges",1);

    int thresh = 96;
    createTrackbar( " Canny thresh:", "edges", &thresh, 255, NULL );
    int deziSigma = 15;
    createTrackbar( " GaussianBlur:", "edges", &deziSigma, 100, NULL );

    while(true){
        cap >> frame;
        cvtColor(frame, edges, CV_BGR2GRAY);
        GaussianBlur(edges, edges, Size(7,7), deziSigma / 10., deziSigma / 10.);
        Canny(edges, edges, thresh, thresh * 2, 3);
        findContours( edges, contours, hierarchy, CV_RETR_TREE, CV_CHAIN_APPROX_SIMPLE, Point(0, 0) );

        Mat drawing = Mat::zeros( edges.size(), CV_8UC3 );
        printf("Found %d contours:", contours.size());
        // Draw contours
        for( int i = 0; i < contours.size(); i++ ){
            printf( "-- % 5d ", contours[i].size() );
            Scalar color = Scalar( 255, 0, 255 );
            drawContours( drawing, contours, i, color, 2, 8, hierarchy, 0, Point() );
        }
        printf("\n");

        imshow("edges", drawing);
        if(waitKey(30) >= 0)
            break;
    }
    return 0;
}
