#!/usr/bin/perl
#<trkpt lat="44.095955342" lon="9.865295558">
#        <ele>66.193885</ele>
#        <time>2005-11-30T09:36:20Z</time>
#        <speed>0.000000</speed>
#        <name>TP3128</name>
#      </trkpt>
use strict;

# Next line determines what format is output 
my $format=0;
#print "No,Latitude,Longitude,Name,Altitude,Date,Speed,Time\n";
print "No,Latitude,Longitude,Name,Altitude,Date\n" if($format==1);
print "Time,Latitude,Longitude,Name,Elevation,Speed\n" if($format==0);
my ($lat,$lon,$ele,$time,$speed,$name);
my $cnt=0;
while(<>)
{
    if($_=~m|<trkpt lat="(\d+\.\d+)" lon="(\d+\.\d+)">|)
    {
        $lat=$1;
	$lon=$2;
	
    }
    if($_=~m|<ele>(\d+\.\d+)</ele>|)
    {
	$ele=$1
    }
    if($_=~m|<time>(.*)</time>|)
    {
	$time=$1;
    }
    if($_=~m|<speed>(\d+\.\d+)</speed>|)
    {
	$speed=$1;
    }
    if($_=~m|<name>(.*)</name>|)
    {
	$name=$1;
    }
    if($_=~m|</trkpt>|)
    {
	#	print $lat.",".$lon.",".$name.",".$ele.",".$speed.",".$time."\n";
	#	print $lat.",".$lon.",".$name.",".$ele.",".$speed.",".$time."\n";
# unics
	#	No,Latitude,Longitude,Name,Altitude,Date,Time
	$cnt+=1;
#	"No,Latitude,Longitude,Name,Altitude,Date,Time";	
	print $cnt.",".$lat.",".$lon.",".$name.",".$ele.",".$time."\n" if($format==1);
# print "Time,Latitude,Longitude,Name,Altitude,Date,Speed\n" if($format=0);
	print $time.",".$lat.",".$lon.",".$name.",".$ele.",".$speed."\n" if($format==0);	
    }
  
}
